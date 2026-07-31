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
    arch = 'arm64' if platform.machine() == 'arm64' else 'x64'
    binpath = f'macos-{arch}/clingo'
elif platform.system() == 'Windows':
    binpath = 'win/clingo.exe'
else:
    raise SystemError(f"System '{system}' is not supported.")
bindir = Path(__file__).resolve().parent / 'bin' / binpath.split('/')[0]
fname = str(bindir / binpath.split('/')[1])


def bundled_site_packages():
    """The bundled interpreter's own site-packages, or None.

    Where _cffi_backend lives -- the module clingo's embedded Python needs
    before it can run a single #script (python) block.
    """
    found = sorted(bindir.glob('lib/python3.*/site-packages'))
    return found[0] if found else None


def run_clingo():
    # clingo's embedded Python scripting (#script (python)) needs its own
    # bundled stdlib (see fetch_clingo.py), not whatever Python the host
    # happens to have. PYTHONHOME points it there, and PYTHONPATH names the
    # bundled site-packages -- both explicitly, so that nothing about the
    # host's own Python installations can decide otherwise. Windows doesn't
    # need this: it's pinned via a *_pth file placed next to the binary.
    #
    # Setting PYTHONPATH rather than merely clearing it is what 5.8.0 got
    # wrong: with the package installed in a virtualenv and that virtualenv
    # activated -- the normal way to use it -- the embedded interpreter came
    # up with no site-packages on sys.path at all, and every #script (python)
    # died on a missing _cffi_backend, silently yielding no model.
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    if system in ('Linux', 'Darwin'):
        env['PYTHONHOME'] = str(bindir)
        site_packages = bundled_site_packages()
        if site_packages:
            env['PYTHONPATH'] = str(site_packages)
    subprocess.call([fname] + sys.argv[1:], env=env)
