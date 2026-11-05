"""Supervise API and queue consumer as independent processes in a small Render service."""
import os
import signal
import subprocess
import sys
import time


def main():
    children = []
    stopping = False

    def shutdown(*_):
        nonlocal stopping
        stopping = True
        for process in children:
            if process.poll() is None:
                process.terminate()

    previous_handlers = {sig: signal.signal(sig, shutdown) for sig in (signal.SIGTERM, signal.SIGINT)}
    exit_code = 0
    try:
        commands = [
            [sys.executable, '-m', 'uvicorn', 'backend.main:app', '--host', '0.0.0.0',
             '--port', os.getenv('PORT', '8000'), '--no-access-log', '--proxy-headers',
             '--forwarded-allow-ips', os.getenv('TRUSTED_PROXY_IPS', '127.0.0.1')],
            [sys.executable, '-m', 'backend.worker'],
        ]
        if os.getenv('OFFSITE_BACKUP_ENABLED', 'false').lower() == 'true':
            commands.append([sys.executable, '-m', 'scripts.offsite_backup'])
        for command in commands:
            if stopping:
                break
            children.append(subprocess.Popen(command))
        while not stopping:
            for process in children:
                if process.poll() is not None:
                    exit_code = process.returncode or 1
                    shutdown()
                    break
            time.sleep(.5)
    finally:
        # Startup failures must also stop children already launched successfully.
        try:
            shutdown()
            deadline = time.monotonic() + 25
            for process in children:
                try:
                    process.wait(timeout=max(.1, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        finally:
            for sig, handler in previous_handlers.items():
                signal.signal(sig, handler)
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
