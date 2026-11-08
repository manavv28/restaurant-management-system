"""Run both development services; stop the entire process groups on exit."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

root=Path(__file__).resolve().parent.parent
processes=[]
def stop(*_):
    for process in processes:
        try:os.killpg(process.pid,signal.SIGTERM)
        except ProcessLookupError:pass
    for process in processes:
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass

signal.signal(signal.SIGTERM,lambda *_:sys.exit(0))
try:
    processes.append(subprocess.Popen([str(root/'.venv/bin/python'),'-m','uvicorn','app.main:app','--host','0.0.0.0','--port','8000'],cwd=root/'backend',start_new_session=True))
    processes.append(subprocess.Popen(['npm','run','dev'],cwd=root/'frontend',start_new_session=True))
    while all(p.poll() is None for p in processes):time.sleep(.3)
    sys.exit(next((p.returncode for p in processes if p.returncode is not None),1))
except KeyboardInterrupt:pass
finally:stop()
