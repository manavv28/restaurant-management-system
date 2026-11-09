"""Single-service entry point: private API + public Next.js standalone server."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parent.parent
children=[]

def cleanup():
    for child in children:
        if child.poll() is None:
            try: os.killpg(child.pid,signal.SIGTERM)
            except ProcessLookupError: pass
    for child in children:
        try: child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            try: os.killpg(child.pid,signal.SIGKILL)
            except ProcessLookupError: pass

def terminate(*_): raise SystemExit(0)

signal.signal(signal.SIGTERM,terminate)
try:
    children.append(subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000'],cwd=ROOT/'backend',start_new_session=True))
    deadline=time.monotonic()+90
    while True:
        if children[0].poll() is not None: raise RuntimeError('Backend exited during startup')
        try:
            with urlopen('http://127.0.0.1:8000/health',timeout=2) as response:
                if response.status==200: break
        except (URLError,TimeoutError): pass
        if time.monotonic()>deadline: raise RuntimeError('Backend readiness timed out')
        time.sleep(.5)
    if os.getenv('CATALOG_WORKER_ENABLED','false').lower()=='true':
        children.append(subprocess.Popen([sys.executable,'-m','app.catalog_worker','--seed-osm','--loop'],cwd=ROOT/'backend',start_new_session=True))
    env={**os.environ,'HOSTNAME':'0.0.0.0','PORT':os.getenv('PORT','10000')}
    children.append(subprocess.Popen(['node','server.js'],cwd=ROOT/'frontend',env=env,start_new_session=True))
    while all(child.poll() is None for child in children): time.sleep(.5)
    raise SystemExit(next((c.returncode or 1 for c in children if c.poll() is not None),1))
except KeyboardInterrupt: pass
finally: cleanup()
