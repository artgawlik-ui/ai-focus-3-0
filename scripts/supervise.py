"""Supervise API and queue consumer as independent processes in a small Render service."""
import os, signal, subprocess, sys, time
children=[]
stopping=False

def shutdown(*_):
    global stopping
    stopping=True
    for process in children:
        if process.poll() is None: process.terminate()

signal.signal(signal.SIGTERM,shutdown)
signal.signal(signal.SIGINT,shutdown)
children.append(subprocess.Popen([sys.executable,'-m','uvicorn','backend.main:app','--host','0.0.0.0','--port',os.getenv('PORT','8000'),'--proxy-headers','--forwarded-allow-ips',os.getenv('TRUSTED_PROXY_IPS','127.0.0.1')]))
children.append(subprocess.Popen([sys.executable,'-m','backend.worker']))
if os.getenv('OFFSITE_BACKUP_ENABLED','false').lower()=='true':
    children.append(subprocess.Popen([sys.executable,'-m','scripts.offsite_backup']))
exit_code=0
try:
    while not stopping:
        for process in children:
            if process.poll() is not None:
                exit_code=process.returncode or 1
                shutdown()
                break
        time.sleep(.5)
finally:
    shutdown()
    deadline=time.monotonic()+25
    for process in children:
        try: process.wait(timeout=max(.1,deadline-time.monotonic()))
        except subprocess.TimeoutExpired: process.kill(); process.wait()
sys.exit(exit_code)
