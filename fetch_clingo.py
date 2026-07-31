#!/usr/bin/env python3
"""Fetch a self-contained clingo binary for the current OS from conda-forge,
and place it (with its private runtime libs, if any) in clyngor_with_clingo/bin/<os>/.

This replaces the old retrieve-clingo.sh, which downloaded prebuilt archives
from clingo's GitHub releases page. Since clingo 5.4.0, potassco no longer
publishes those prebuilt binaries there -- only source tarballs. conda-forge
still builds and publishes real per-OS binaries for every release, so we grab
those instead and make them relocatable (no conda env needed at runtime).

Usage: python fetch_clingo.py <clingo-version> [conda-executable]

"""
import os
import sys
import glob
import shutil
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_NAME = 'clyngor-fetch-clingo'

# conda-forge builds link Python in with a "with Python" configuration, but
# not Lua. This is an intentional trade-off documented in the README: it
# covers `#script (python)` blocks (the common case) but not `#script (lua)`.


def sh(*args, **kwargs):
    print('+', ' '.join(str(a) for a in args), file=sys.stderr)
    subprocess.run(args, check=True, **kwargs)


def conda_bin(explicit):
    return explicit or shutil.which('micromamba') or shutil.which('mamba') or shutil.which('conda')


def create_env(conda, version):
    sh(conda, 'create', '-y', '-n', ENV_NAME, '-c', 'conda-forge', f'clingo={version}')


def env_prefix(conda):
    out = subprocess.run([conda, 'env', 'list'], check=True, capture_output=True, text=True).stdout
    for line in out.splitlines():
        parts = line.split()
        if parts and parts[0] == ENV_NAME:
            return Path(parts[-1])
    raise RuntimeError(f"could not find prefix of conda env {ENV_NAME!r} in:\n{out}")


def bundle_python_home(prefix, outdir):
    """Copy conda's lib/pythonX.Y/ (stdlib, lib-dynload, site-packages with
    _cffi_backend) so PYTHONHOME=outdir works standalone. Without this, the
    embedded interpreter has no stdlib to import (not even `encodings`), and
    -- worse -- CPython's path-search heuristic can silently wander off and
    pick up an unrelated Python installation found elsewhere on the host.
    """
    pylibdir = next((prefix / 'lib').glob('python3.*'))
    ignore = shutil.ignore_patterns('__pycache__', '*.pyc')
    shutil.copytree(pylibdir, outdir / 'lib' / pylibdir.name, ignore=ignore, dirs_exist_ok=True)


def relocate_linux(prefix, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    binary = prefix / 'bin' / 'clingo'
    shutil.copy2(binary, outdir / 'clingo')
    needed = subprocess.run(
        ['ldd', str(binary)], check=True, capture_output=True, text=True
    ).stdout
    for line in needed.splitlines():
        line = line.strip()
        if '=>' not in line:
            continue
        libname, _, rest = line.partition('=>')
        libpath = rest.strip().split(' ')[0]
        if libpath and str(prefix) in libpath:
            # only the conda-provided libs need bundling; system libs
            # (libc, libpthread, libm...) are assumed present everywhere.
            shutil.copy2(libpath, outdir / os.path.basename(libpath))
    sh('patchelf', '--set-rpath', '$ORIGIN', str(outdir / 'clingo'))
    bundle_python_home(prefix, outdir)


def _macho_deps(path):
    out = subprocess.run(
        ['otool', '-L', str(path)], check=True, capture_output=True, text=True
    ).stdout
    return [line.strip().split(' ')[0] for line in out.splitlines()[1:]]


def relocate_macos(prefix, outdir):
    # conda-forge mach-o binaries reference their private libs as
    # @rpath/libfoo.dylib (or @loader_path/), with an LC_RPATH pointing at
    # the env's lib/ dir -- which stops existing once relocated. Copy every
    # such dependency (transitively) next to the binary and add
    # @loader_path to its rpath so they resolve in-place. Anything else
    # (absolute /usr/lib etc.) is a system lib, left alone.
    outdir.mkdir(parents=True, exist_ok=True)
    binary = prefix / 'bin' / 'clingo'
    shutil.copy2(binary, outdir / 'clingo')
    todo, seen = [outdir / 'clingo'], set()
    while todo:
        img = todo.pop()
        for dep in _macho_deps(img):
            if dep.startswith('@rpath/') or dep.startswith('@loader_path/'):
                name = os.path.basename(dep)
            elif dep.startswith(str(prefix)):
                name = os.path.basename(dep)
                sh('install_name_tool', '-change', dep, f'@rpath/{name}', str(img))
            else:
                continue
            if name in seen:
                continue
            seen.add(name)
            src = prefix / 'lib' / name
            if src.exists():
                shutil.copy2(src, outdir / name)
                todo.append(outdir / name)
    sh('install_name_tool', '-add_rpath', '@loader_path', str(outdir / 'clingo'))
    # modifying a mach-o invalidates its code signature, and arm64 macOS
    # refuses to run unsigned binaries -- re-sign everything ad-hoc.
    for f in ['clingo', *seen]:
        if (outdir / f).exists():
            sh('codesign', '--force', '--sign', '-', str(outdir / f))
    bundle_python_home(prefix, outdir)


def relocate_windows(prefix, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    # conda-forge's windows build puts clingo.exe/clingo.dll under
    # Library/bin; Windows resolves DLLs from the executable's own folder
    # by default, so co-locating those is enough on its own. But clingo's
    # embedded Python scripting needs a full, working Python: the stdlib
    # (Lib/), compiled extension modules (DLLs/), the python DLL itself,
    # and cffi's _cffi_backend (used to bridge into libclingo). Without an
    # explicit *_pth file, CPython's path-search heuristic can wander off
    # and pick up an unrelated Python installation from the host machine
    # instead of the one bundled here (this is exactly what happened when
    # this was first tried on a GitHub Actions runner: it silently loaded
    # AWS CLI's bundled Python and failed to find `_cffi_backend`).
    libdir = prefix / 'Library' / 'bin'
    shutil.copy2(libdir / 'clingo.exe', outdir / 'clingo.exe')
    for dll in glob.glob(str(libdir / '*.dll')):
        shutil.copy2(dll, outdir / os.path.basename(dll))

    python_dll = next(prefix.glob('python3*.dll'))
    shutil.copy2(python_dll, outdir / python_dll.name)

    ignore = shutil.ignore_patterns('__pycache__', '*.pyc')
    shutil.copytree(prefix / 'Lib', outdir / 'Lib', ignore=ignore, dirs_exist_ok=True)
    shutil.copytree(prefix / 'DLLs', outdir / 'DLLs', ignore=ignore, dirs_exist_ok=True)

    # pin sys.path to only the bundled locations, ignoring the registry,
    # PATH, and any other Python install found on the host machine.
    pth_name = python_dll.stem + '._pth'  # e.g. python314._pth
    (outdir / pth_name).write_text('Lib\nLib\\site-packages\nDLLs\n.\n\nimport site\n')


def runtime_env(outdir):
    """The env clingo needs at runtime: same as what run_clingo() in
    clyngor_with_clingo/__init__.py sets up, so the smoke test here
    actually exercises the real runtime path."""
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    if platform.system() in ('Linux', 'Darwin'):
        env['PYTHONHOME'] = str(outdir)
    return env


def smoke_test(outdir, exe):
    script = ROOT / '_smoke_test.lp'
    script.write_text(
        '#script (python)\n'
        'def main(prg):\n'
        '    prg.ground([("base", [])])\n'
        '    prg.solve(on_model=lambda m: print("SMOKE_TEST_MODEL:", m))\n'
        '#end.\n'
        'a. b :- a.\n'
    )
    out = subprocess.run(
        [str(outdir / exe), str(script), '0'],
        capture_output=True, text=True, env=runtime_env(outdir),
    )
    script.unlink()
    if 'SMOKE_TEST_MODEL: a b' not in out.stdout:
        raise SystemExit(
            f"smoke test failed for {outdir / exe}\n"
            f"stdout:\n{out.stdout}\nstderr:\n{out.stderr}"
        )
    print(f"smoke test OK for {outdir / exe}", file=sys.stderr)


def main():
    version = sys.argv[1]
    conda = conda_bin(sys.argv[2] if len(sys.argv) > 2 else None)
    if not conda:
        raise SystemExit("no micromamba/mamba/conda executable found on PATH")

    create_env(conda, version)
    prefix = env_prefix(conda)

    system = platform.system()
    if system == 'Linux':
        outdir = ROOT / 'clyngor_with_clingo' / 'bin' / 'linux'
        relocate_linux(prefix, outdir)
        smoke_test(outdir, 'clingo')
    elif system == 'Darwin':
        arch = 'arm64' if platform.machine() == 'arm64' else 'x64'
        outdir = ROOT / 'clyngor_with_clingo' / 'bin' / f'macos-{arch}'
        relocate_macos(prefix, outdir)
        smoke_test(outdir, 'clingo')
    elif system == 'Windows':
        outdir = ROOT / 'clyngor_with_clingo' / 'bin' / 'win'
        relocate_windows(prefix, outdir)
        smoke_test(outdir, 'clingo.exe')
    else:
        raise SystemExit(f"unsupported system: {system}")


if __name__ == '__main__':
    main()
