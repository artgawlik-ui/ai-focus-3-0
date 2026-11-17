"""Bezpieczne lokalne odczyty eksportu. Moduł nie łączy się z Render ani Meta."""
import gzip,hashlib,json,re,tarfile
from pathlib import Path,PurePosixPath

MAX_ARCHIVE=128*1024*1024
MAX_EXPANDED=256*1024*1024
MAX_MEMBERS=2048
MAX_ROWS=250000

class ExportError(ValueError):
    """Wyłącznie stałe kategorie błędów, bez danych i ścieżek z archiwum."""


def inspect_archive(path):
    path=Path(path)
    if not path.is_file() or not 0<path.stat().st_size<=MAX_ARCHIVE:raise ExportError('archive_size')
    sha=hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda:source.read(65536),b''):sha.update(chunk)
    # Tar może zakończyć odczyt przed trailerem gzip: osobno wymuszamy CRC/EOF.
    expanded=0
    try:
        with gzip.open(path,'rb') as source:
            for chunk in iter(lambda:source.read(65536),b''):
                expanded+=len(chunk)
                if expanded>MAX_EXPANDED:raise ExportError('expanded_size')
        with tarfile.open(path,'r:gz') as archive:
            seen=set();members=[];tocs=[];total=0
            for member in archive:
                if len(members)>=MAX_MEMBERS:raise ExportError('member_limit')
                name=PurePosixPath(member.name)
                if name.is_absolute() or '..' in name.parts or '\\' in member.name or any(ord(c)<32 for c in member.name) or len(member.name)>500:raise ExportError('unsafe_path')
                if not (member.isfile() or member.isdir()):raise ExportError('unsafe_member_type')
                key=str(name)
                if key in seen:raise ExportError('duplicate_path')
                seen.add(key);members.append(member)
                total+=member.size
                if total>MAX_EXPANDED:raise ExportError('expanded_size')
                if member.isfile():
                    if name.name=='toc.dat':tocs.append(name)
                    elif not re.fullmatch(r'[0-9]+\.dat(?:\.gz)?',name.name):raise ExportError('unexpected_file')
            if len(tocs)!=1:raise ExportError('toc_count')
            parent=tocs[0].parent
            if any(m.isfile() and PurePosixPath(m.name).parent!=parent for m in members):raise ExportError('multiple_dump_directories')
            return {'archive_bytes':path.stat().st_size,'archive_sha256':sha.hexdigest(),'gzip_crc_verified':True,'members':len(members),'unpacked_file_bytes':total,'data_files':sum(m.isfile() for m in members)-1,'toc_path':str(tocs[0])}
    except ExportError:raise
    except (OSError,EOFError,tarfile.TarError):raise ExportError('invalid_archive') from None


def extract_checked(path,destination):
    info=inspect_archive(path);destination=Path(destination)
    # Nowy katalog eliminuje podmianę plików/symlinków z poprzedniej próby.
    destination.mkdir(mode=0o700,parents=False,exist_ok=False)
    with tarfile.open(path,'r:gz') as archive:
        for member in archive:
            relative=PurePosixPath(member.name);target=destination.joinpath(*relative.parts)
            if member.isdir():target.mkdir(mode=0o700,parents=True,exist_ok=True)
            else:
                target.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
                with archive.extractfile(member) as source,target.open('xb') as output:
                    target.chmod(0o600)
                    for chunk in iter(lambda:source.read(65536),b''):output.write(chunk)
    return destination/info['toc_path'],info


def fingerprint_rows(rows):
    """SHA-256 multizbioru skrótów wierszy COPY; bez zapisu surowych danych."""
    hashes=[]
    for row in rows:
        if len(hashes)>=MAX_ROWS:raise ExportError('row_limit')
        hashes.append(hashlib.sha256(row.removesuffix(b'\n')).digest())
    return {'count':len(hashes),'sha256':hashlib.sha256(b''.join(sorted(hashes))).hexdigest()}


def source_copy_fingerprints(lines):
    result={};table=None;rows=[];columns=None
    for line in lines:
        if table:
            if line.rstrip(b'\r\n')==b'\\.':
                result[table]={'columns':columns,**fingerprint_rows(rows)};table=None;rows=[]
            else:
                if len(rows)>=MAX_ROWS:raise ExportError('row_limit')
                rows.append(line)
            continue
        if line.startswith(b'COPY '):
            match=re.fullmatch(rb'COPY (?:"public"|public)\.((?:"[a-z_][a-z0-9_]*"|[a-z_][a-z0-9_]*)) \(([^)]+)\) FROM stdin;\r?\n?',line)
            if not match:raise ExportError('unsupported_copy_header')
            table=match[1].decode('ascii').strip('"');columns=[x.strip().strip('"') for x in match[2].decode('ascii').split(',')]
            if any(not re.fullmatch(r'[a-z_][a-z0-9_]*',x) for x in columns) or table in result:raise ExportError('unsupported_copy_header')
    if table:raise ExportError('incomplete_copy')
    return result


def json_fingerprint(rows):
    canonical=sorted(json.dumps(json.loads(x),sort_keys=True,ensure_ascii=False,separators=(',',':')) for x in rows)
    return {'count':len(canonical),'sha256':hashlib.sha256('\n'.join(canonical).encode()).hexdigest()}


def expected_orm_schema():
 import os
 from sqlalchemy import String,Text,Integer,PrimaryKeyConstraint,UniqueConstraint,ForeignKeyConstraint
 # Import modeli nie może nawet skonfigurować połączenia produkcyjnego.
 saved=os.environ.get('DATABASE_URL');os.environ['DATABASE_URL']='sqlite://'
 try:
  from backend.db import Base
  from backend import meta_models
 finally:
  if saved is None:os.environ.pop('DATABASE_URL',None)
  else:os.environ['DATABASE_URL']=saved
 columns=[];constraints=[];indexes=[]
 for table in Base.metadata.sorted_tables:
  for column in table.columns:
   kind='text' if isinstance(column.type,Text) else 'character varying'+('('+str(column.type.length)+')' if column.type.length else '') if isinstance(column.type,String) else 'integer' if isinstance(column.type,Integer) else 'unsupported'
   columns.append([table.name,column.name,kind,column.nullable])
  for c in table.constraints:
   if isinstance(c,PrimaryKeyConstraint):constraints.append(['p',table.name,[v.name for v in c.columns],None,None])
   elif isinstance(c,UniqueConstraint):constraints.append(['u',table.name,[v.name for v in c.columns],None,None])
   elif isinstance(c,ForeignKeyConstraint):constraints.append(['f',table.name,[v.name for v in c.columns],c.elements[0].column.table.name,[e.column.name for e in c.elements]])
  for i in table.indexes:indexes.append([table.name,bool(i.unique),[c.name for c in i.columns]])
 columns.append(['alembic_version','version_num','character varying(32)',False]);constraints.append(['p','alembic_version',['version_num'],None,None])
 return {'columns':columns,'constraints':constraints,'indexes':indexes}
