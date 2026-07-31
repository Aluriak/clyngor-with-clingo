# clyngor-with-clingo — notes for Claude Code

Ships a working `clingo` executable on the user's PATH, so people who
cannot "install the clingo binary yourself" just `pip install
clyngor-with-clingo`. The python code is ~30 lines; **the release pipeline
is the whole product**, and it is where every bug has been.

Package version tracks the clingo version it ships (5.8.0 ships clingo
5.8.0).

## Where the binaries come from

Potassco stopped publishing prebuilt per-OS binaries on clingo's GitHub
releases page **after 5.4.0** (source tarballs only). `retrieve-clingo.sh`
and `put-clingo-version.sh` depend on those archives and therefore only
work for versions **<= 5.4.0**; they are kept for rebuilding old versions.

For anything newer, `fetch_clingo.py` fetches the binary from
**conda-forge** (which still builds all three OSes for every release) and
makes it relocatable:

- **Linux**: copy the conda-provided `.so`s, `patchelf --set-rpath $ORIGIN/lib`
- **macOS**: rewrite `@rpath`/prefix-absolute deps, add an `@loader_path/lib`
  rpath, then **ad-hoc re-sign** every touched mach-o (arm64 macOS refuses
  binaries whose signature `install_name_tool` invalidated)
- **Windows**: co-locate DLLs, plus a `pythonXY._pth` to pin `sys.path`

It runs one OS at a time; `.github/workflows/build-binaries.yml` runs it on
all of them (workflow_dispatch, and reusable via workflow_call) and
smoke-tests each binary natively with an embedded `#script (python)`.

## Hard-won details — do not regress these

- **Bundle the python stdlib, not just the shared libs.** clingo's embedded
  python needs a real stdlib next to it (`PYTHONHOME` on Linux/macOS, a
  `._pth` on Windows). Without it the interpreter wanders off and loads
  whatever python it finds on the host — on a GitHub runner it picked up
  AWS CLI's bundled python and died on `_cffi_backend`.
- **Walk deps from the extension modules too**, not only from the binary:
  `_cffi_backend` pulls `libffi`, which the binary itself never references.
- **Testing relocation requires actually removing the source conda env.**
  With it still on disk at its original path, a "relocated" binary silently
  resolves back to it and every test passes for the wrong reason.
- **`sqlite3` and `tkinter` are pruned** from the bundled stdlib: conda's
  libsqlite3 drags in a 39 MB ICU, tkinter drags tcl/tk, and neither has
  any business inside an ASP solver.
- **One platform-tagged wheel per OS/arch**, no sdist. A single fat wheel
  would blow past PyPI's 100 MB per-file limit; an sdist would install with
  no binaries at all.
- **conda-forge builds have python scripting but no Lua.**
- `macos-13` was retired by GitHub on 2025-12-04 — jobs targeting it queue
  forever. macOS runners are arm64 now; x86_64 lives on as `macos-15-intel`
  until fall 2027.

## Releasing

`git tag vX.Y.Z && git push origin vX.Y.Z` triggers
`.github/workflows/python-publish.yml`: it builds the binaries on all four
targets, **refuses to publish if any binary is under 100 KB**, then builds
and uploads the four wheels.

That size guard exists because of **issue #5**: `bin/` used to hold empty
placeholder files committed to git (the real binaries were only ever on the
maintainer's machine), and when the publish workflow was added it happily
shipped those placeholders to PyPI as v5.4.0. The placeholders are gone
from git now — `bin/` is populated from CI artifacts only.
