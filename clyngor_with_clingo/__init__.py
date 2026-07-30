"""This is the sole file of the clyngor-with-clingo package.

This package is just here to populate user's path with a clingo executable,
here implemented using subprocess.

"""

import os
import sys
import platform
import subprocess
from pathlib import Path

system = platform.system()
if platform.system() == 'Linux':
    binpath = 'linux/clingo'
elif platform.system() == 'Darwin':
    binpath = 'macos/clingo'
elif platform.system() == 'Windows':
    binpath = 'win/clingo.exe'
else:
    raise SystemError(f"System '{system}' is not supported.")
bindir = Path(__file__).resolve().parent / 'bin' / binpath.split('/')[0]
fname = str(bindir / binpath.split('/')[1])


def run_clingo():
    # clingo's embedded Python scripting (#script (python)) needs its own
    # bundled stdlib (see fetch_clingo.py), not whatever Python the host
    # happens to have. PYTHONHOME points it there; clearing PYTHONPATH
    # avoids the host's own Python picking a fight over sys.path. Windows
    # doesn't need this: it's pinned via a *_pth file placed next to the
    # binary instead.
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    if system in ('Linux', 'Darwin'):
        env['PYTHONHOME'] = str(bindir)
    subprocess.call([fname] + sys.argv[1:], env=env)
