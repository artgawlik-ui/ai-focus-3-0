"""Wyłącznie syntetyczne archiwa; bez dostępu do produkcji lub Dockera."""
import gzip,io,tarfile
import pytest
from scripts.export_validation import inspect_archive,extract_checked,source_copy_fingerprints,fingerprint_rows,ExportError


def archive(tmp_path,entries):
    path=tmp_path/'fixture.dir.tar.gz'
    with tarfile.open(path,'w:gz') as target:
        for name,kind,body in entries:
            item=tarfile.TarInfo(name);item.type=kind;item.size=len(body) if kind==tarfile.REGTYPE else 0
            if kind in (tarfile.SYMTYPE,tarfile.LNKTYPE):item.linkname='/outside'
            target.addfile(item,io.BytesIO(body) if kind==tarfile.REGTYPE else None)
    return path


def test_archive_crc_sha_private_extraction(tmp_path):
    path=archive(tmp_path,[('dump/toc.dat',tarfile.REGTYPE,b'fixture'),('dump/1.dat',tarfile.REGTYPE,b'row\n')])
    info=inspect_archive(path);assert info['data_files']==1 and info['gzip_crc_verified']
    toc,copy=extract_checked(path,tmp_path/'isolated')
    assert toc.read_bytes()==b'fixture' and toc.stat().st_mode&0o777==0o600
    assert info==copy
    with pytest.raises(FileExistsError):extract_checked(path,tmp_path/'isolated')


@pytest.mark.parametrize('name,kind',[('../escape.dat',tarfile.REGTYPE),('/escape.dat',tarfile.REGTYPE),('dump/x.dat',tarfile.SYMTYPE),('dump/x.dat',tarfile.LNKTYPE),('dump/x.dat',tarfile.FIFOTYPE),('dump/../x.dat',tarfile.REGTYPE)])
def test_unsafe_archives_rejected(tmp_path,name,kind):
    path=archive(tmp_path,[('dump/toc.dat',tarfile.REGTYPE,b'x'),(name,kind,b'x')])
    with pytest.raises(ExportError):inspect_archive(path)


def test_duplicate_and_truncated_archives(tmp_path):
    path=archive(tmp_path,[('dump/toc.dat',tarfile.REGTYPE,b'x'),('dump/toc.dat',tarfile.REGTYPE,b'x')])
    with pytest.raises(ExportError):inspect_archive(path)
    path=archive(tmp_path,[('dump/toc.dat',tarfile.REGTYPE,b'x')]);path.write_bytes(path.read_bytes()[:-5])
    with pytest.raises(ExportError):inspect_archive(path)


def test_limits_checked_before_extraction(tmp_path,monkeypatch):
    path=archive(tmp_path,[('dump/toc.dat',tarfile.REGTYPE,b'x'*100)])
    monkeypatch.setattr('scripts.export_validation.MAX_EXPANDED',50)
    with pytest.raises(ExportError):inspect_archive(path)


def test_copy_fingerprints_order_duplicates_escaped_rows():
    data=b'COPY public.users (id, name) FROM stdin;\n1\tExample\\nName\n2\t\\N\n\\.\n'
    first=source_copy_fingerprints(data.splitlines(keepends=True))['users']
    assert first['count']==2 and first['columns']==['id','name']
    assert fingerprint_rows([b'b\n',b'a\n'])==fingerprint_rows([b'a\n',b'b\n'])
    assert fingerprint_rows([b'a\n',b'a\n'])!=fingerprint_rows([b'a\n'])
    with pytest.raises(ExportError):source_copy_fingerprints(data.splitlines(keepends=True)[:-1])


def test_quoted_pg17_identifiers():
    rows=source_copy_fingerprints(b'COPY "public"."users" ("id", "name") FROM stdin;\n1\tFixture\n\\.\n'.splitlines(keepends=True))
    assert rows['users']['columns']==['id','name'] and rows['users']['count']==1


@pytest.mark.parametrize('mode',['production','wrong_hash','url'])
def test_cli_guards_never_spawn_restore_or_expose_input(tmp_path,mode):
    import subprocess,sys,os,json
    path=archive(tmp_path,[('dump/toc.dat',tarfile.REGTYPE,b'fixture')])
    output=tmp_path/'result.json'
    argument='https://example.invalid/export?token=fixture-sensitive' if mode=='url' else str(path)
    result=subprocess.run([sys.executable,'-m','scripts.isolated_export_restore','--archive',argument,'--sha256','0'*64,'--output',str(output)],env={**os.environ,'APP_ENV':'production' if mode=='production' else 'test'},capture_output=True,text=True)
    data=json.loads(output.read_text());assert result.returncode==1 and data['status']=='BLOCKED'
    assert data['error_category']=={'production':'production_runtime_forbidden','wrong_hash':'archive_sha256_mismatch','url':'archive_size'}[mode]
    assert data['temporary_plaintext_removed'] and 'isolation' not in data
    assert 'fixture-sensitive' not in result.stdout+result.stderr+output.read_text()


def test_import_cannot_trigger_restore(monkeypatch):
    import subprocess,importlib
    def forbidden(*args,**kwargs):raise AssertionError('Import nie może uruchamiać procesów')
    monkeypatch.setattr(subprocess,'run',forbidden)
    module=importlib.import_module('scripts.isolated_export_restore')
    assert callable(module.main)


def test_synthetic_restore_override_is_strict_and_sanitized(tmp_path):
    import subprocess,sys,os,json
    output=tmp_path/'result.json'
    result=subprocess.run([sys.executable,'-m','scripts.isolated_export_restore','--archive',str(tmp_path/'absent'),'--sha256','0'*64,'--output',str(output),'--synthetic-source-name','unapproved-fixture'],env={**os.environ,'APP_ENV':'test'},capture_output=True,text=True)
    data=json.loads(output.read_text())
    assert result.returncode==1 and data['error_category']=='invalid_synthetic_source_name'
    assert 'unapproved-fixture' not in result.stdout+result.stderr+output.read_text()
    assert data['temporary_plaintext_removed'] and 'isolation' not in data
