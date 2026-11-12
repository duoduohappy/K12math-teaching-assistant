"""Start a checked local server, without proxying loopback requests."""
import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

root = Path(__file__).resolve().parent
os.chdir(root)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
# Let Windows choose a free port rather than reusing a possibly stale service.
with socket.socket() as probe:
    probe.bind(('127.0.0.1', 0))
    port = probe.getsockname()[1]
env = dict(os.environ, TEACHING_PORT=str(port))
child = subprocess.Popen([sys.executable, str(root / 'server.py')], env=env)
url = f'http://127.0.0.1:{port}/workflow'
try:
    ready = False
    for _ in range(40):
        if child.poll() is not None:
            raise RuntimeError(f'Server exited with code {child.returncode}')
        try:
            with opener.open(url, timeout=1) as r:
                ready = r.status == 200 and '教学闭环' in r.read().decode('utf-8')
            if ready: break
        except (OSError, urllib.error.URLError):
            time.sleep(.25)
    if not ready:
        raise RuntimeError('Local HTTP check failed. No browser was opened. See errors above.')
    print(f'HTTP 200 verified: {url}', flush=True)
    print('Keep this window open. Press Ctrl+C to stop.', flush=True)
    webbrowser.open(url)
    child.wait()
except KeyboardInterrupt:
    pass
except Exception as exc:
    print(f'Startup failed: {exc}', flush=True)
finally:
    if child.poll() is None:
        child.terminate()
        child.wait(timeout=5)
