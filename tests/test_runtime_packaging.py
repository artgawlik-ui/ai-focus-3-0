"""Build actual runtime COPY instructions without network or running the image."""
import io,os,subprocess,sys,tarfile,uuid
import pytest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('baseline',[False,True])
def test_runtime_copy_artifact_has_usable_native_migration_profile(tmp_path,baseline):
    # Only Git-tracked runtime sources enter this local context, never reports/secrets.
    context=tmp_path/'context';context.mkdir()
    names=subprocess.check_output(['git','ls-files','backend','migrations','scripts','requirements.txt','alembic.ini','native-alembic.ini'],cwd=ROOT,text=True).splitlines()
    for name in names:
        source=ROOT/name
        if not source.is_file():continue
        dest=context/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(source.read_bytes())
    recipe=subprocess.check_output(['git','show','80f4652:Dockerfile'],cwd=ROOT,text=True) if baseline else (ROOT/'Dockerfile').read_text()
    runtime=recipe.split('\nFROM ')[-1]
    copies=[line for line in runtime.splitlines() if line.startswith('COPY ') and not line.startswith('COPY --from=')]
    (context/'Dockerfile').write_text('FROM scratch\nWORKDIR /app\n'+'\n'.join(copies)+'\n')
    env={k:v for k,v in os.environ.items() if k not in ('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH','BUILDX_BUILDER','BUILDKIT_HOST')}
    env['BUILDX_CONFIG']=str(tmp_path/'buildx')
    docker=['docker','--host=unix:///var/run/docker.sock']
    image='focus3-packaging-'+uuid.uuid4().hex[:12];container=image+'-artifact'
    created=False
    try:
        built=subprocess.run(docker+['build','--network=none','--pull=false','-t',image,'.'],cwd=context,env=env,capture_output=True,timeout=60)
        assert built.returncode==0,'Local runtime COPY artifact build failed'
        subprocess.run(docker+['create','--name',container,image,'/not-started'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=15);created=True
        raw=subprocess.check_output(docker+['export',container],env=env,stderr=subprocess.DEVNULL,timeout=15)
        artifact=tmp_path/'artifact';artifact.mkdir()
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            for member in archive.getmembers():
                parts=Path(member.name).parts
                if not member.isfile() or not parts or parts[0]!='app' or '..' in parts:continue
                dest=artifact/Path(*parts[1:]);dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes(archive.extractfile(member).read())
        # Execute Alembic discovery from the resulting filesystem, not repository cwd.
        for config,revision in [('alembic.ini','004'),('native-alembic.ini','007')]:
            result=subprocess.run([sys.executable,'-m','alembic','-c',config,'heads'],cwd=artifact,capture_output=True,timeout=15)
            if baseline and config=='native-alembic.ini':
                assert not (artifact/config).exists() and result.returncode!=0
            else:
                assert result.returncode==0,'Packaged migration profile is missing or unusable: '+config
                assert result.stdout.decode().split()[0]==revision
    finally:
        if created:subprocess.run(docker+['rm','-f',container],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
        subprocess.run(docker+['image','rm','-f',image],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
