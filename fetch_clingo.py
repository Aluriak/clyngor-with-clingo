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


def relocate_macos(prefix, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    binary = prefix / 'bin' / 'clingo'
    shutil.copy2(binary, outdir / 'clingo')
    needed = subprocess.run(
        ['otool', '-L', str(binary)], check=True, capture_output=True, text=True
    ).stdout
    changes = []
    for line in needed.splitlines()[1:]:
        libpath = line.strip().split(' ')[0]
        if libpath.startswith(str(prefix)):
            libname = os.path.basename(libpath)
            shutil.copy2(prefix / libpath[len(str(prefix)) + 1:], outdir / libname)
            changes += ['-change', libpath, f'@loader_path/{libname}']
    if changes:
        sh('install_name_tool', *changes, str(outdir / 'clingo'))


def relocate_windows(prefix, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    # conda-forge's windows build puts binaries/DLLs under Library/bin;
    # Windows resolves DLLs from the executable's own folder by default,
    # so co-locating everything from there is enough, no patching needed.
    libdir = prefix / 'Library' / 'bin'
    shutil.copy2(libdir / 'clingo.exe', outdir / 'clingo.exe')
    for dll in glob.glob(str(libdir / '*.dll')):
        shutil.copy2(dll, outdir / os.path.basename(dll))


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
        capture_output=True, text=True,
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
        outdir = ROOT / 'clyngor_with_clingo' / 'bin' / 'macos'
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
