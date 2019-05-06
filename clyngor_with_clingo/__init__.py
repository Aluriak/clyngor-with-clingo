"""This is the sole file of the clyngor-with-clingo package.

This package is just here to populate user's path with a clingo executable,
here implemented using subprocess.

"""

import sys
import platform
import subprocess
import pkg_resources

system = platform.system()
if platform.system() == 'Linux':
    binpath = 'linux/clingo'
elif platform.system() == 'Darwin':
    binpath = 'macos/clingo'
elif platform.system() == 'Windows':
    binpath = 'win/clingo.exe'
else:
    raise SystemError(f"System '{system}' is not supported.")
fname = pkg_resources.resource_filename(__name__, 'bin/' + binpath)
def run_clingo():
    subprocess.call([fname] + sys.argv[1:])
