"""Write the OpenAPI document to api/openapi.json.

The spec is committed and CI fails if regenerating it produces a diff. Without that
check the contract quietly drifts from the code, and "one contract, many clients"
(docs/03-architecture.md) becomes something we merely say rather than something that
is true.

Usage:  python scripts/export_openapi.py [--check]

Run from ``api/`` with the venv active.
"""

import json
import os
import pathlib
import sys

# Importing the app must not require a reachable database.
os.environ.setdefault("CONSTELLATE_DATABASE_URL", "sqlite://")

import constellate  # noqa: E402
from constellate.main import app  # noqa: E402

TARGET = pathlib.Path(__file__).resolve().parent.parent / "openapi.json"
#: Where this checkout's constellate package must live. ``python scripts/export_openapi.py``
#: without the right ``PYTHONPATH`` silently imports the main checkout's ``constellate``
#: instead and produces a contract that reflects that tree, not this worktree's —
#: ``main()`` checks the import against this path and refuses rather than exporting wrong.
_EXPECTED_PKG = pathlib.Path(__file__).resolve().parent.parent / "src" / "constellate"


def main() -> int:
    """Write the spec, or with ``--check`` verify the committed one is current."""
    imported_pkg = pathlib.Path(constellate.__file__).resolve().parent
    if imported_pkg != _EXPECTED_PKG:
        print(
            f"wrong constellate package imported:\n"
            f"  got:      {imported_pkg}\n"
            f"  expected: {_EXPECTED_PKG}\n"
            "Set PYTHONPATH=<repo>/api/src or activate the worktree's own venv."
        )
        return 1

    spec = app.openapi()
    current = json.dumps(spec, indent=2, sort_keys=True) + "\n"

    if "--check" in sys.argv:
        if not TARGET.exists():
            print(f"{TARGET.name} is missing; run: python scripts/export_openapi.py")
            return 1
        if TARGET.read_text(encoding="utf-8") != current:
            print(
                f"{TARGET.name} is out of date.\n"
                "The API changed without the committed contract being updated.\n"
                "Run: python scripts/export_openapi.py"
            )
            return 1
        print(f"{TARGET.name} is up to date")
        return 0

    TARGET.write_text(current, encoding="utf-8", newline="\n")
    print(f"wrote {TARGET.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
