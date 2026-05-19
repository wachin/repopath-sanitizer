"""Development shim for the source-layout package.

The project uses ``src/repopath_sanitizer`` as the maintained package.  This
small shim keeps ``python -m repopath_sanitizer`` working from a source checkout
without importing the older prototype modules that still live beside it.
"""

from pathlib import Path

_src_pkg = Path(__file__).resolve().parent.parent / "src" / "repopath_sanitizer"
if _src_pkg.is_dir():
    __path__.insert(0, str(_src_pkg))

__all__ = ["__version__"]
__version__ = "0.1.0"
