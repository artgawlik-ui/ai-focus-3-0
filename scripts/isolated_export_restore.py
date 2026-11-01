"""Jednorazowy odizolowany restore; nigdy nie używa produkcyjnego DATABASE_URL."""
import hashlib,io,json,os,re,shutil,subprocess,tarfile,time,uuid
from pathlib import Path
from datetime import datetime,timezone
from scripts.export_validation import inspect_archive,extract_checked,source_copy_fingerprints,fingerprint_rows,json_fingerprint,ExportError

def main():
    import argparse,tempfile
    parser=argparse.ArgumentParser(description='Lokalny, bezsieciowy test eksportu Focus 3; bez operacji produkcyjnych')
    parser.add_argument('--archive',required=True);parser.add_argument('--sha256',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args()
    archive_path=Path(args.archive)
    work=tempfile.TemporaryDirectory(prefix='focus3-export-check-')
    root=Path(work.name)
    report={'status':'BLOCKED','production_writes':0,'app_started':False,'paid_resources_created':0}
    name='focus3-export-'+uuid.uuid4().hex[:10]
    env={k:v for k,v in os.environ.items() if k not in ('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH')}
    docker=['docker','--host=unix:///var/run/docker.sock']
    started=False
    pg_restore=Path(__file__).resolve().parents[1]/'.tools/pg_restore'
    if not pg_restore.is_file():pg_restore=Path('/usr/lib/postgresql/17/bin/pg_restore')
    if not pg_restore.is_file():pg_restore=Path(shutil.which('pg_restore') or '/nonexistent/pg_restore')
    validation_started=time.monotonic()

    def run(args,input=None,timeout=60):
     p=subprocess.run(args,input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=timeout)
     if p.returncode:
      report['last_error']={'category':'local_command_failed','exit':p.returncode,'stderr_sha256':hashlib.sha256(p.stderr).hexdigest()}
      raise ExportError('local_command_failed')
     return p.stdout

    def sql(query,database='restored'):
     return run(docker+['exec','-i','--user','postgres',name,'psql','-X','-qAt','-v','ON_ERROR_STOP=1','-U','postgres','-d',database],query.encode())

    def value(query):return json.loads(sql(query).decode())

    try:
     if os.getenv('APP_ENV')=='production':raise ExportError('production_runtime_forbidden')
     info=inspect_archive(archive_path)
     if info['archive_sha256']!=args.sha256:raise ExportError('archive_sha256_mismatch')
     toc,info=extract_checked(archive_path,root/'validated');dump=toc.parent
     report['archive']={k:v for k,v in info.items() if k!='toc_path'}
     toc_list=run([str(pg_restore),'--list',str(dump)]).decode()
     report['toc']={}
     for key,pattern in {'database_version':r'Dumped from database version: ([^\n]+)','pg_dump_version':r'Dumped by pg_dump version: ([^\n]+)','archive_created_at':r'Archive created at ([^\n]+)','format':r'Format: ([^\n]+)'}.items():
      m=re.search(pattern,toc_list);report['toc'][key]=m[1].strip() if m else None
     report['toc']['database_name_matches_expected']=bool(re.search(r'dbname: ai_focus_3_0_db(?:\n|$)',toc_list))
     if not report['toc']['database_name_matches_expected']:raise ExportError('unexpected_database')
     report['toc']['header_entries']=int(re.search(r'TOC Entries: ([0-9]+)',toc_list)[1])
     report['toc']['entries']=len([l for l in toc_list.splitlines() if l and not l.startswith(';')])
     tables=re.findall(r'^\d+; \d+ \d+ TABLE DATA public ([a-z_][a-z0-9_]*) ',toc_list,re.M)
     if len(tables)!=info['data_files']:raise ExportError('toc_data_file_count')
     source_sql=run([str(pg_restore),'--data-only','--no-owner','--no-acl','--file=-',str(dump)])
     source=source_copy_fingerprints(source_sql.splitlines(keepends=True));del source_sql
     if set(tables)!=set(source):raise ExportError('copy_table_count')
     report['source_tables']=len(source)
     # Obraz już obecny lokalnie; --pull=never wyklucza pobieranie i zmianę obrazu.
     image=run(docker+['image','inspect','postgres:17','--format','{{.Id}}']).decode().strip()
     run(docker+['run','--pull=never','--detach','--name',name,'--network','none','--log-driver','none','--read-only','--user','postgres','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','512m','--cpus','0.5','--tmpfs','/var/lib/postgresql/data:rw,nosuid,noexec,size=256m,mode=1777','--tmpfs','/var/run/postgresql:rw,nosuid,noexec,size=16m,mode=1777','--tmpfs','/tmp:rw,nosuid,noexec,size=128m,mode=1777','-e','PGDATA=/var/lib/postgresql/data/isolated','-e','POSTGRES_HOST_AUTH_METHOD=trust','-e','HTTP_PROXY=','-e','HTTPS_PROXY=','-e','ALL_PROXY=','-e','NO_PROXY=','-e','http_proxy=','-e','https_proxy=','-e','all_proxy=','-e','no_proxy=','-e','META_ENABLED=false','-e','META_OAUTH_ENABLED=false','-e','META_WEBHOOK_VERIFY_ENABLED=false','-e','META_INGEST_ENABLED=false','-e','META_CRM_HISTORY_ENABLED=false','-e','META_DIAGNOSTICS_ENABLED=false','-e','META_DM_TRANSPORT_ENABLED=false','-e','OFFSITE_BACKUP_ENABLED=false',image,'postgres','-c',"listen_addresses=",'-c','max_worker_processes=0','-c','shared_preload_libraries=','-c','autovacuum=off'])
     started=True
     for _ in range(80):
      p=subprocess.run(docker+['exec',name,'pg_isready','-U','postgres'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
      if p.returncode==0:break
      time.sleep(.1)
     else:raise ExportError('local_postgres_readiness')
     details=json.loads(run(docker+['inspect',name]))[0]
     report['isolation']={'network_mode':details['HostConfig']['NetworkMode'],'log_driver':details['HostConfig']['LogConfig']['Type'],'read_only_rootfs':details['HostConfig']['ReadonlyRootfs'],'host_mounts':sum(m.get('Type')=='bind' for m in details['Mounts']),'memory_bytes':details['HostConfig']['Memory'],'image_id':image,'proxy_variables_empty':all(not dict(x.split('=',1) for x in details['Config']['Env']).get(k) for k in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','http_proxy','https_proxy','all_proxy','no_proxy')),'all_meta_flags_false':all(dict(x.split('=',1) for x in details['Config']['Env']).get(k)=='false' for k in ('META_ENABLED','META_OAUTH_ENABLED','META_WEBHOOK_VERIFY_ENABLED','META_INGEST_ENABLED','META_CRM_HISTORY_ENABLED','META_DIAGNOSTICS_ENABLED','META_DM_TRANSPORT_ENABLED'))}
     if report['isolation']['network_mode']!='none' or report['isolation']['log_driver']!='none' or report['isolation']['host_mounts']!=0 or not report['isolation']['proxy_variables_empty'] or not report['isolation']['all_meta_flags_false']:raise ExportError('isolation_failed')
     run(docker+['exec','--user','postgres',name,'mkdir','-m','700','/tmp/dump'])
     tar=io.BytesIO()
     with tarfile.open(fileobj=tar,mode='w') as output:
      for path in sorted(dump.iterdir()):output.add(path,arcname=path.name,recursive=False)
     run(docker+['exec','-i','--user','postgres',name,'tar','--no-same-owner','-xf','-','-C','/tmp/dump'],tar.getvalue());tar.close()
     run(docker+['exec','--user','postgres',name,'createdb','-U','postgres','restored'])
     begin=time.monotonic()
     run(docker+['exec','--user','postgres',name,'pg_restore','--no-owner','--no-acl','--single-transaction','--exit-on-error','-U','postgres','-d','restored','/tmp/dump'])
     report['restore_seconds']=round(time.monotonic()-begin,3)
     report['tables']={}
     for table,expected in source.items():
      columns=','.join('"'+c+'"' for c in expected['columns'])
      data=sql("SET TIME ZONE 'UTC'; SET DateStyle='ISO'; COPY public.\""+table+'" ('+columns+') TO STDOUT;')
      actual=fingerprint_rows(data.splitlines(keepends=True))
      json_rows=sql('SELECT row_to_json(t)::text FROM public."'+table+'" t;').decode().splitlines()
      report['tables'][table]={'export_copy':{k:v for k,v in expected.items() if k!='columns'},'restored_copy':actual,'copy_matches':actual=={k:v for k,v in expected.items() if k!='columns'},'restored_json':json_fingerprint(json_rows)}
     if not all(t['copy_matches'] for t in report['tables'].values()):raise ExportError('export_row_fingerprint_mismatch')
     report['revision']=sql('SELECT version_num FROM alembic_version;').decode().strip()
     if report['revision']!='004':raise ExportError('unexpected_revision')
     report['schema']={}
     for key,query in {
     'columns':"SELECT json_build_array(table_name,column_name,data_type,udt_name,is_nullable,column_default,character_maximum_length) FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name,ordinal_position",
     'indexes':"SELECT json_build_array(tablename,indexname,indexdef) FROM pg_indexes WHERE schemaname='public' ORDER BY tablename,indexname",
     'constraints':"SELECT json_build_array(c.relname,k.conname,k.contype,pg_get_constraintdef(k.oid)) FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' ORDER BY c.relname,k.conname"}.items():
      rows=sql(query+';').decode().splitlines();report['schema'][key]=json_fingerprint(rows)
     report['schema']['expected_tables']=sorted(source)
     report['schema']['table_count']=len(json.loads(sql("SELECT coalesce(json_agg(tablename ORDER BY tablename),'[]') FROM pg_tables WHERE schemaname='public';")))
     # Porównanie struktury odtworzonego punktu z ORM bieżącego main/3.0.3.
     from scripts.export_validation import expected_orm_schema
     expected=expected_orm_schema()
     queries={
     'columns':"SELECT json_build_array(c.relname,a.attname,format_type(a.atttypid,a.atttypmod),NOT a.attnotnull) FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r' AND a.attnum>0 AND NOT a.attisdropped ORDER BY c.relname,a.attnum",
     'constraints':"SELECT json_build_array(k.contype,c.relname,(SELECT json_agg(a.attname ORDER BY x.ord) FROM unnest(k.conkey) WITH ORDINALITY x(num,ord) JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum=x.num),r.relname,(SELECT json_agg(a.attname ORDER BY x.ord) FROM unnest(k.confkey) WITH ORDINALITY x(num,ord) JOIN pg_attribute a ON a.attrelid=k.confrelid AND a.attnum=x.num)) FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace LEFT JOIN pg_class r ON r.oid=k.confrelid WHERE n.nspname='public' ORDER BY c.relname,k.conname",
     'indexes':"SELECT json_build_array(t.relname,i.indisunique,(SELECT json_agg(a.attname ORDER BY x.ord) FROM unnest(i.indkey) WITH ORDINALITY x(num,ord) JOIN pg_attribute a ON a.attrelid=t.oid AND a.attnum=x.num)) FROM pg_index i JOIN pg_class t ON t.oid=i.indrelid JOIN pg_namespace n ON n.oid=t.relnamespace WHERE n.nspname='public' AND NOT EXISTS(SELECT 1 FROM pg_constraint k WHERE k.conindid=i.indexrelid) ORDER BY t.relname,i.indexrelid"}
     report['orm_compatibility']={}
     for key,query in queries.items():
      actual=json_fingerprint(sql(query+';').decode().splitlines())
      expected_hash=json_fingerprint([json.dumps(x) for x in expected[key]])
      report['orm_compatibility'][key]={'matches':actual==expected_hash,'actual':actual,'expected':expected_hash}
     if not all(x['matches'] for x in report['orm_compatibility'].values()):raise ExportError('orm_schema_mismatch')
     source_types={}
     for item in toc_list.splitlines():
      m=re.match(r'^\d+; \d+ \d+ (TABLE DATA|FK CONSTRAINT|CONSTRAINT|INDEX|TABLE)\b',item)
      if m:source_types[m[1]]=source_types.get(m[1],0)+1
     actual_types=value("SELECT json_build_object('TABLE',(SELECT count(*) FROM pg_tables WHERE schemaname='public'),'FK CONSTRAINT',(SELECT count(*) FROM pg_constraint k JOIN pg_namespace n ON n.oid=k.connamespace WHERE n.nspname='public' AND k.contype='f'),'CONSTRAINT',(SELECT count(*) FROM pg_constraint k JOIN pg_namespace n ON n.oid=k.connamespace WHERE n.nspname='public' AND k.contype!='f'));")
     actual_types['INDEX']=report['orm_compatibility']['indexes']['actual']['count'];actual_types['TABLE DATA']=len(report['tables'])
     report['toc_schema_comparison']={'source':source_types,'restored':actual_types,'matches':source_types==actual_types}
     if source_types!=actual_types:raise ExportError('toc_schema_mismatch')
     export_time=datetime.strptime(report['toc']['archive_created_at'],'%Y-%m-%d %H:%M:%S UTC').replace(tzinfo=timezone.utc).isoformat()
     report['snapshot_time_evaluation_utc']=export_time
     report['statuses']={}
     for key,query in {
     'inbox':"SELECT coalesce(json_agg(x),'[]') FROM (SELECT status,dead_letter,count(*) FROM meta_webhook_inbox GROUP BY status,dead_letter) x",
     'credentials':"SELECT json_build_object('total',count(*),'active',count(*) FILTER(WHERE revoked=0),'missing_ciphertext',count(*) FILTER(WHERE revoked=0 AND token_ciphertext='')) FROM meta_credentials",
     'refresh':"SELECT coalesce(json_agg(x),'[]') FROM (SELECT status,count(*) FROM meta_refresh_states GROUP BY status) x",
     'technical':"SELECT json_build_object('total',count(*),'active',count(*) FILTER(WHERE active=1)) FROM users WHERE email='verification@focus.invalid'",
     'technical_sessions_at_export':"SELECT count(*) FROM sessions s JOIN users u ON u.id=s.user_id WHERE u.email='verification@focus.invalid' AND s.expires::timestamptz>'"+export_time+"'::timestamptz",
     'runtime':"SELECT json_build_object('listen_addresses',current_setting('listen_addresses'),'max_worker_processes',current_setting('max_worker_processes'),'preload',current_setting('shared_preload_libraries'))"}.items():report['statuses'][key]=value(query+';')
     owner_email=os.getenv('FOCUS_RESTORE_OWNER_EMAIL','')
     if owner_email:
      from psycopg import sql as pgsql
      literal=pgsql.Literal(owner_email).as_string()
      report['statuses']['owner_active_at_export']=value("SELECT to_json(count(*)=1) FROM users WHERE active=1 AND role='manager' AND email="+literal+';')
     # Nie wypisujemy żadnych rekordów klientów, haseł, sesji ani tokenów.
     report['status']='RESTORE_AND_EXPORT_POINT_INTEGRITY_PASS'
    except Exception as error:
     report['error_category']=str(error) if isinstance(error,ExportError) else type(error).__name__
    finally:
     if started:
      try:run(docker+['rm','--force','--volumes',name]);report['isolated_container_removed']=True
      except Exception:
       report['isolated_container_removed']=False;report['status']='BLOCKED';report['error_category']='cleanup_failed'
     work.cleanup();report['temporary_plaintext_removed']=True
     report['total_validation_seconds']=round(time.monotonic()-validation_started,3)
     output_path=Path(args.output);output_path.parent.mkdir(parents=True,exist_ok=True)
     output_path.write_text(json.dumps(report,indent=2)+'\n')
     print(json.dumps({'status':report['status'],'production_writes':0,'paid_resources_created':0,'container_removed':report.get('isolated_container_removed',False),'temporary_plaintext_removed':report.get('temporary_plaintext_removed',False)}))
     if report['status']!='RESTORE_AND_EXPORT_POINT_INTEGRITY_PASS':raise SystemExit(1)


if __name__=='__main__':
    main()
