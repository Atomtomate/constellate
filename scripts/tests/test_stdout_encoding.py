"""Every runnable script sets stdout to UTF-8 before it prints this repo's prose.

Python gives stdout the console's codec, cp1252 on this machine, and what these scripts
print is notes, briefs and report headings -- prose full of en dashes and arrows. A script
without the line dies partway through its output on the first one it meets, which is how
`review_briefs.py` failed inside the mandatory pre-review pass (#184). The line is one
statement at the top of `main()`; this is what keeps a new script from shipping without it.
"""

import ast
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]


def reconfigures_stdout(tree: ast.Module) -> bool:
    """Does the module call `sys.stdout.reconfigure(encoding="utf-8", ...)` anywhere?"""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        stream = node.func.value
        if node.func.attr != "reconfigure" or not isinstance(stream, ast.Attribute):
            continue
        if stream.attr == "stdout" and any(
            kw.arg == "encoding" and getattr(kw.value, "value", None) == "utf-8"
            for kw in node.keywords
        ):
            return True
    return False


class StdoutEncodingTest(unittest.TestCase):
    def test_every_runnable_script_reconfigures_stdout(self):
        missing = []
        for path in sorted(SCRIPTS.glob("*.py")):
            source = path.read_text(encoding="utf-8")
            # a module nobody runs prints through its caller, which has the line already
            if '__name__ == "__main__"' not in source:
                continue
            if not reconfigures_stdout(ast.parse(source)):
                missing.append(path.name)
        self.assertEqual(missing, [], f"no sys.stdout.reconfigure in: {', '.join(missing)}")


if __name__ == "__main__":
    unittest.main()
