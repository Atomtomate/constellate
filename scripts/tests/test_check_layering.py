"""Table-driven tests for `scripts/check_layering.py`.

`docs/03-architecture.md`'s "Layers inside the API package" is the authority these tests
pin; a change to the rule starts there, not here.

Stdlib-only (`unittest`), so they run on the same bare interpreter the script does -- no
venv, nothing installed -- matching `scripts/README.md`'s rule for everything here. Run
them with `python -m unittest discover scripts/tests` or
`python scripts/tests/test_check_layering.py`.

Each case writes a tiny `constellate`-shaped package into a temp directory and runs the
real `check()` over it, asserting on the lines it prints rather than on internals.
Assertions are by substring, not whole-list equality, so a case pins the finding it is
about and not the exact wording of every other line.

The `sources/` cases are the ones `docs/03` asks for by name: the sibling's check has no
place for `sources/`, so a port that changed only its constants would place an adapter
outside the layers, where an unreached module is an entry point free to import anything,
and would see nothing in `from constellate.sources import spotify`, since `sources` is no
layer it knows. Both of those pass a constants-only port; each is pinned here to fail it.

A single-file fixture with one outcome is a row in `CASES`, run by one looping test
(`test_cases`); anything that spans multiple files, checks more than one path, or needs
two receivers stays a function. A snippet drops what the check does not use, since
`check()` only ever parses a fixture with `ast.parse` and never runs it -- except where
the check's own logic depends on the shape: an unannotated parameter, for one, only reads
as unannotated inside a real `def`.
"""

import sys
import tempfile
import textwrap
import unittest
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import check_layering  # noqa: E402

#: The fragment every `sources/`-side finding carries, and no other finding does -- what
#: the two tests `docs/03` demands assert on, so that a finding from the generic direction
#: check (which a constants-only port would also print for some shapes) cannot satisfy
#: them by accident.
ADAPTER_RULE = "a source imports only domain/ and the leaves"
#: The same for the layer side: a layer reaching an adapter.
INTERFACE_RULE = "through the interface it declares"


@dataclass(frozen=True)
class Case:
    """One `check()` fixture, and the substrings its printed lines must, or must not, show.

    A field left `None` is a check this case does not make. `finding_lacks=""` and
    `exception_lacks=""` both mean "nothing printed for this path at all", not "this exact
    substring is absent": `"" in line` is always true, so the empty string reads as the
    whole line.
    """

    label: str
    path: str
    source: str
    finding_has: str | None = None
    finding_lacks: str | None = None
    exception_has: str | None = None
    exception_lacks: str | None = None


CASES: list[Case] = [
    # -- SQL: built and run in repos/ only ----------------------------------------------------
    Case("module_alias_constructor_is_sql", "services/x.py",
         "import sqlalchemy as sa; sa.select(1)\n", finding_has="sa.select("),
    Case("bare_module_import_constructor_is_sql", "services/x.py",
         "import sqlalchemy; sqlalchemy.insert(1)\n", finding_has="sqlalchemy.insert("),
    Case("session_get_is_a_primary_key_select", "services/x.py", """
        from sqlalchemy.orm import Session
        def load(session: Session): return session.get(object, 1)
        """, finding_has=".get("),
    Case(
        # Every router and dependency annotates the session `SessionDep`, never bare
        # `Session` (`api/deps.py`) -- the alias has to be recognised by name, not just the
        # type it stands for, or every router-level `session.get(...)` slips past unseen.
        "sessiondep_get_is_a_primary_key_select", "api/routers/x.py", """
        from constellate.api.deps import SessionDep
        def load(session: SessionDep): return session.get(object, 1)
        """, finding_has=".get("),
    Case(
        # `Session | None` (PEP 604) is still a `Session` for `.get(...)`'s purposes -- an
        # optional receiver is not a reason this stops being a primary-key select.
        "union_none_session_get_is_a_primary_key_select", "services/x.py", """
        from sqlalchemy.orm import Session
        def load(session: Session | None): return session.get(object, 1)
        """, finding_has=".get("),
    Case("from_sqlalchemy_import_submodule_constructor_is_sql", "services/x.py",
         "from sqlalchemy import sql; sql.select(1)\n", finding_has="sql.select("),
    Case("dotted_import_module_alias_constructor_is_sql", "services/x.py",
         "import sqlalchemy.sql as sq; sq.select(1)\n", finding_has="sq.select("),
    Case(
        # `server_default=sa.text(...)` on a `mapped_column` is the standard idiom for a
        # table default -- the same job SQL_CONSTRUCTORS already excuses `func` for.
        "models_text_default_not_flagged", "models/x.py", """
        import sqlalchemy as sa
        from sqlalchemy.orm import mapped_column
        created_at = mapped_column(server_default=sa.text("CURRENT_TIMESTAMP"))
        """, finding_lacks=""),
    Case(
        # `.execute(` is matched by name alone (`SQL_EXECUTORS`), not by a typed receiver --
        # a model executing a query is wrong on any receiver, not just a real `Session`.
        "models_execute_is_a_violation", "models/x.py",
        'x.execute("select 1")\n', finding_has=".execute("),
    Case(
        # The `models/` exemption is `text()` only, not the whole constructor half --
        # `sa.select(2)` building a query is exactly as wrong there as anywhere else.
        "models_other_constructor_is_still_a_violation", "models/x.py",
        "import sqlalchemy as sa; default_scope = sa.select(2)\n",
        finding_has="sa.select(", exception_lacks=""),
    Case("dict_get_is_not_sql", "services/x.py",
         'def read(data: dict): return data.get("key")\n', finding_lacks=".get("),
    Case("unannotated_get_is_not_sql", "services/x.py",
         'def read(thing): return thing.get("key")\n', finding_lacks=".get("),
    Case(
        # `file_layer("repos/core.py") == "repos"` short-circuits `check_sql` before it
        # looks at the body at all -- the early return the rest of this table exists
        # because of.
        "repos_may_build_and_run_sql", "repos/core.py", """
        from sqlalchemy import select
        def rows(session): return session.execute(select(1))
        """, finding_lacks=""),
    Case(
        # An adapter knows an external API or a file format, never SQL (docs/03): the
        # general rule reaches it like any module outside repos/, with no exemption.
        "adapter_running_sql_is_a_violation", "sources/spotify.py", """
        from sqlalchemy import select
        def rows(session): return session.execute(select(1))
        """, finding_has="repos/ is the only module that knows SQL"),

    # -- direction, and the domain rule -------------------------------------------------------
    Case("import_against_the_direction_is_flagged", "services/x.py",
         "from constellate.api import deps\n", finding_has="against"),
    Case("domain_importing_a_layer_is_flagged", "domain/x.py",
         "from constellate.models import Event\n", finding_has=""),
    Case("domain_importing_domain_is_fine", "domain/x.py",
         "from constellate.domain import events\n", finding_lacks=""),
    Case("layer_importing_domain_stays_fine", "services/x.py",
         "from constellate.domain import events\n", finding_lacks=""),
    Case(
        # `poll.py` sits above `api/` in the chain, not outside it: reaching into `repos/`
        # or any other layer is downward from there, never a direction violation.
        "entry_point_may_reach_any_layer", "poll.py",
        "from constellate.repos import core\n", finding_lacks=""),

    # -- sources/: the rule the sibling's check has no place for (docs/03) -------------------
    Case("adapter_importing_repos_is_flagged", "sources/spotify.py",
         "from constellate.repos import events\n", finding_has=ADAPTER_RULE),
    Case("adapter_importing_models_is_flagged", "sources/spotify.py",
         "from constellate.models import Event\n", finding_has=ADAPTER_RULE),
    Case(
        # Structurally, not by subclassing: an adapter that imports the Protocol to inherit
        # from it has made `sources/` depend on `services/`, the very edge the seam cuts.
        "adapter_importing_the_interface_is_flagged", "sources/spotify.py",
        "from constellate.services.sources import SourceAdapter\n", finding_has=ADAPTER_RULE),
    Case("adapter_importing_api_is_flagged", "sources/spotify.py",
         "from constellate.api import errors\n", finding_has=ADAPTER_RULE),
    Case("adapter_importing_domain_is_fine", "sources/spotify.py",
         "from constellate.domain import events\n", finding_lacks=""),
    Case("adapter_importing_its_own_package_is_fine", "sources/spotify/client.py",
         "from constellate.sources.spotify import auth\n", finding_lacks=""),
    Case("service_importing_an_adapter_by_path_is_flagged", "services/ingest.py",
         "from constellate.sources.spotify import SpotifyAdapter\n", finding_has=INTERFACE_RULE),
    Case(
        # The by-name shape, `from constellate import sources`, has to be seen exactly as the
        # by-path one -- `imported` rewrites it so every check keys on the module.
        "service_importing_an_adapter_by_name_is_flagged", "services/ingest.py",
        "from constellate import sources\n", finding_has=INTERFACE_RULE),
    Case("router_importing_an_adapter_is_flagged", "api/routers/x.py",
         "from constellate.sources import spotify\n", finding_has=INTERFACE_RULE),
    Case("repo_importing_an_adapter_is_flagged", "repos/x.py",
         "from constellate.sources import spotify\n", finding_has=INTERFACE_RULE),
    Case("model_importing_an_adapter_is_flagged", "models/x.py",
         "from constellate.sources import spotify\n", finding_has=INTERFACE_RULE),
    Case(
        # `domain/` uses nothing, and an adapter is no exception -- caught by the domain
        # rule, which fires before the sources rule gets a turn.
        "domain_importing_an_adapter_is_flagged", "domain/x.py",
        "from constellate.sources import spotify\n", finding_has="uses nothing"),
    Case(
        # The one place that may name both: the entry point hands the service its adapter.
        "entry_point_hands_a_service_its_adapter", "poll.py", """
        from constellate.services import ingest
        from constellate.sources import spotify
        """, finding_lacks=""),

    # -- the health.py readiness-probe carve-out (docs/03, Conventions) -----------------------
    Case("health_readiness_probe_is_a_sanctioned_exception", "api/routers/health.py", """
        from sqlalchemy import text

        def ready(session):
            session.execute(text("select 1"))
        """, finding_lacks="", exception_has="readiness probe"),
    Case(
        # The sanction is keyed on the statement, `select 1`, not on the file: a different
        # query in `health.py` is not the readiness probe and stays a violation.
        "health_other_sql_is_still_a_violation", "api/routers/health.py", """
        from sqlalchemy import select

        def other(session):
            session.execute(select(Event))
        """, finding_has="", exception_lacks=""),
    Case("sql_elsewhere_is_still_flagged", "api/routers/other.py", """
        from sqlalchemy import text

        def go(session):
            session.execute(text("select 1"))
        """, finding_has=""),

    # -- only logging_config.py may configure logging ------------------------------------------
    Case("addhandler_outside_logging_config_is_violation", "services/x.py",
         "logger.addHandler(h)\n", finding_has="addHandler"),
    Case(
        # The receiver is an attribute (`logging.root`), not a bare name.
        "addhandler_on_logging_root_is_violation", "services/x.py",
        "logging.root.addHandler(h)\n", finding_has="addHandler"),
    Case(
        # `self.log` is a receiver the check has no way to know is a logger.
        "addhandler_on_self_attribute_is_violation", "services/x.py",
        "self.log.addHandler(h)\n", finding_has="addHandler"),
    Case("basicconfig_via_module_alias_is_violation", "services/x.py",
         "logging.basicConfig(level=logging.DEBUG)\n", finding_has="basicConfig"),
    Case("dictconfig_via_direct_import_is_violation", "api/routers/x.py",
         "from logging.config import dictConfig; dictConfig({})\n", finding_has="dictConfig"),
    Case(
        # The receiver is a dotted attribute chain, not a name bound by `from ... import`.
        "dictconfig_via_module_dotted_call_is_violation", "api/routers/x.py",
        "import logging.config; logging.config.dictConfig({})\n", finding_has="dictConfig"),
    Case("setlevel_on_getlogger_result_is_violation", "services/x.py",
         "logging.getLogger(__name__).setLevel(logging.DEBUG)\n", finding_has="setLevel"),
    Case("setlevel_on_imported_getlogger_chain_is_violation", "services/x.py",
         'from logging import getLogger; getLogger("x").setLevel("DEBUG")\n',
         finding_has="setLevel"),
    Case(
        # Flagged even on a non-logger -- the false positive `check_logging_cfg`'s
        # docstring accepts.
        "setlevel_on_an_unrelated_receiver_is_also_flagged", "services/x.py", """
        class Slider:
            def setLevel(self, v): self.v = v
        Slider().setLevel(5)
        """, finding_has="setLevel"),
    Case("removehandler_outside_logging_config_is_violation", "services/x.py",
         'logging.getLogger("x").removeHandler(h)\n', finding_has="removeHandler"),
    Case("fileconfig_call_outside_logging_config_is_violation", "services/x.py",
         'import logging.config; logging.config.fileConfig("logging.ini")\n',
         finding_has="fileConfig"),
    Case(
        # Flagged at the import itself -- matching only the callee's name would miss the
        # call `bc()` entirely.
        "aliased_from_import_of_a_config_function_is_violation", "services/x.py",
        "from logging import basicConfig as bc; bc()\n", finding_has="imports basicConfig"),
    Case("assigning_handlers_outside_logging_config_is_violation", "services/x.py",
         'logging.getLogger("constellate").handlers = []\n', finding_has="uses handlers"),
    Case(
        # `logger.propagate = False` silently detaches a logger from its handler.
        "assigning_propagate_outside_logging_config_is_violation", "services/x.py",
        'logging.getLogger("constellate").propagate = False\n', finding_has="uses propagate"),
    Case(
        # A read of `.handlers` followed by a call -- not an assignment target.
        "clearing_handlers_outside_logging_config_is_violation", "services/x.py",
        'logging.getLogger("constellate").handlers.clear()\n', finding_has="uses handlers"),
    Case(
        # The assignment target is the subscript, not the `.handlers` attribute itself.
        "slice_assigning_handlers_outside_logging_config_is_violation", "services/x.py",
        'logging.getLogger("constellate").handlers[:] = []\n', finding_has="uses handlers"),
    Case("augmenting_handlers_outside_logging_config_is_violation", "services/x.py",
         'logging.getLogger("constellate").handlers += [h]\n', finding_has="uses handlers"),
    Case(
        # A read of `.handlers` followed by a mutating call.
        "appending_to_handlers_outside_logging_config_is_violation", "services/x.py",
        'logging.getLogger("constellate").handlers.append(h)\n', finding_has="uses handlers"),
]


class CheckLayeringTest(unittest.TestCase):
    """Each check over a fixture package built in a temp directory."""

    def _run(self, files: dict[str, str]) -> tuple[list[str], list[str]]:
        """Write `{relative path: source}` into a temp package root and run every check."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel, src in files.items():
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(textwrap.dedent(src), encoding="utf-8")
            findings, exceptions, _modules = check_layering.check(root)
        return findings, exceptions

    def _assert_case(self, case: Case) -> None:
        """Run one `Case`'s fixture and check every substring it names, or its absence."""
        findings, exceptions = self._run({case.path: case.source})
        if case.finding_has is not None:
            self.assertTrue(
                any(case.path in f and case.finding_has in f for f in findings),
                f"{case.label}: expected a finding for {case.path!r} with {case.finding_has!r}",
            )
        if case.finding_lacks is not None:
            self.assertFalse(
                any(case.path in f and case.finding_lacks in f for f in findings),
                f"{case.label}: unexpected finding for {case.path!r} with "
                f"{case.finding_lacks!r}",
            )
        if case.exception_has is not None:
            self.assertTrue(
                any(case.path in a and case.exception_has in a for a in exceptions),
                f"{case.label}: expected an exception for {case.path!r} with "
                f"{case.exception_has!r}",
            )
        if case.exception_lacks is not None:
            self.assertFalse(
                any(case.path in a and case.exception_lacks in a for a in exceptions),
                f"{case.label}: unexpected exception for {case.path!r} with "
                f"{case.exception_lacks!r}",
            )

    def test_cases(self):
        for case in CASES:
            with self.subTest(case=case.label):
                self._assert_case(case)

    # -- the skip: api/ reaching repos/ past services/ --------------------------------------

    def test_an_api_module_importing_repos_is_a_skip_however_it_spells_the_import(self):
        """A layer imported by name (`from constellate import repos`) must be seen exactly as
        one imported by path (`from constellate.repos import ...`), the shape whose fix the
        sibling found landing unpinned."""
        by_path, _ = self._run(
            {"api/routers/x.py": "from constellate.repos import core as repo\n"}
        )
        by_name, _ = self._run({"api/routers/x.py": "from constellate import repos\n"})
        for findings in (by_path, by_name):
            self.assertTrue(
                any("api/routers/x.py:1" in f and "skipping services/" in f for f in findings)
            )

    def test_an_api_module_importing_models_is_not_a_skip(self):
        """Only `-> repos/` counts (docs/03: "A router that imports from `repos/` has skipped a
        layer"); the ORM classes are every upper layer's ordinary vocabulary."""
        findings, _ = self._run({"api/routers/x.py": "from constellate.models import Event\n"})
        self.assertFalse(any("api/routers/x.py" in f for f in findings))

    # -- the two cases docs/03 asks for by name: each fails a constants-only port -----------

    def test_an_adapter_importing_repos_or_models_is_a_violation(self):
        """With the sibling's constants swapped and nothing else, `sources/spotify.py` sits
        outside the four layers, nothing reaches it, so it is an entry point and free to
        import anything -- `check()` prints nothing for it. The assertion is on the
        `sources/`-side wording, not on "any finding", so only the rule itself satisfies it."""
        for layer in ("repos", "models"):
            with self.subTest(layer=layer):
                findings, _ = self._run(
                    {"sources/spotify.py": f"from constellate.{layer} import thing\n"}
                )
                self.assertTrue(
                    any(
                        "sources/spotify.py:1" in f
                        and f"imports {layer}/" in f
                        and ADAPTER_RULE in f
                        for f in findings
                    ),
                    findings,
                )

    def test_a_service_importing_an_adapter_is_a_violation(self):
        """With the constants swapped and nothing else, `constellate.sources` names no layer
        the check knows, so `import_layer` answers None and the import is skipped as if it
        pointed outside the package. Both spellings, since `imported` rewrites the by-name
        one and a port could get one right and not the other."""
        for source in (
            "from constellate.sources.spotify import SpotifyAdapter\n",
            "from constellate.sources import spotify\n",
            "from constellate import sources\n",
        ):
            with self.subTest(source=source.strip()):
                findings, _ = self._run({"services/ingest.py": source})
                self.assertTrue(
                    any(
                        "services/ingest.py:1" in f
                        and "services/ imports sources/" in f
                        and INTERFACE_RULE in f
                        for f in findings
                    ),
                    findings,
                )

    # -- what an adapter may reach, and what may reach an adapter, across files -------------

    def test_an_adapter_may_import_a_leaf(self):
        """`config.py` and `ids.py` are leaves -- a layer reaches each -- and docs/03 lets an
        adapter import "only `domain/` and the leaves"; the leaves are the half that needs a
        second file to prove."""
        findings, _ = self._run(
            {
                "sources/spotify.py": (
                    "from constellate.config import settings\n"
                    "from constellate.ids import uuid7\n"
                    "from constellate.domain import events\n"
                ),
                "services/x.py": "from constellate.config import settings\n",
                "models/base.py": "from constellate.ids import uuid7\n",
            }
        )
        self.assertFalse(any("sources/spotify.py" in f for f in findings))

    def test_a_leaf_importing_an_adapter_is_a_violation(self):
        """A leaf is usable by every layer, so a leaf that imports an adapter is the path by
        which a service reaches one without naming it."""
        findings, _ = self._run(
            {
                "helpers.py": "from constellate.sources import spotify\n",
                "services/x.py": "from constellate.helpers import thing\n",
            }
        )
        self.assertTrue(
            any("helpers.py:1" in f and "imports sources/" in f and "services/x.py imports it" in f
                for f in findings),
            findings,
        )

    def test_a_module_only_an_adapter_reaches_is_a_leaf(self):
        """What an adapter imports is under the adapter's own rule: a helper only
        `sources/spotify.py` reaches may not import a layer, or the adapter reaches the
        layer through it."""
        findings, _ = self._run(
            {
                "http.py": "from constellate.services import ingest\n",
                "sources/spotify.py": "from constellate.http import get\n",
            }
        )
        self.assertTrue(
            any("http.py:1" in f and "sources/spotify.py imports it" in f for f in findings),
            findings,
        )

    # -- entry point or leaf, the two kinds outside the layers ------------------------------

    def test_leaf_importing_a_layer_is_the_cycle_that_used_to_pass(self):
        """`ids.py` is a leaf because `models/base.py` imports it, so importing `models/`
        back is upward -- and the import cycle Python fails at runtime."""
        findings, _ = self._run(
            {
                "ids.py": "from constellate.models import Event\n",
                "models/base.py": "from constellate.ids import uuid7\n",
            }
        )
        self.assertTrue(
            any("ids.py:1" in f and "models/base.py imports it" in f for f in findings)
        )

    def test_leaf_named_by_the_package_is_still_a_leaf(self):
        """`from constellate import db` places `db.py` exactly as `from constellate.db import
        ...` does -- the same by-name shape the layer side is tested for above."""
        findings, _ = self._run(
            {
                "db.py": "from constellate.repos import core\n",
                "api/deps.py": "from constellate import db\n",
            }
        )
        self.assertTrue(any("db.py:1" in f and "api/deps.py imports it" in f for f in findings))

    def test_leafness_reaches_through_a_leaf(self):
        """One hop only would put a module imported solely by `config.py` back in the
        entry-point default, free to import `api/` from a position under `services/`."""
        findings, _ = self._run(
            {
                "clock.py": "from constellate.api import errors\n",
                "config.py": "from constellate.clock import now\n",
                "services/ingest.py": "from constellate.config import settings\n",
            }
        )
        self.assertTrue(any("clock.py:1" in f and "config.py imports it" in f for f in findings))

    def test_the_package_root_is_a_leaf_no_import_has_to_name(self):
        """Every import of anything in the package runs `__init__.py`, and nothing spells
        `from constellate.__init__ import ...`, so it is a leaf by construction -- otherwise
        a re-export there has `models/` load `services/` at import time."""
        findings, _ = self._run({"__init__.py": "from constellate.services import ingest\n"})
        self.assertTrue(
            any(
                "__init__.py:1" in f and "every import of the package runs it" in f
                for f in findings
            )
        )

    def test_a_module_only_an_entry_point_imports_is_a_leaf(self):
        """`docs/03` has two kinds outside the layers and no third: a module `poll.py` imports
        is reached, so it is a leaf and held to a leaf's rule. The first fixture is the shape
        the check used to pass clean -- `logging_config.py` reaching `api/request_id.py` for
        its filter, so the poller loaded `api/` to write one log line. The second is where
        that import belongs: a leaf of its own, which both the middleware and the filter may
        reach, and which `logging_config.py` may then import beside `config.py`."""
        findings, _ = self._run(
            {
                "logging_config.py": "from constellate.api.request_id import get_request_id\n",
                "poll.py": "from constellate.logging_config import configure_logging\n",
            }
        )
        self.assertTrue(
            any(
                "logging_config.py:1" in f and "imports api/" in f and "poll.py imports it" in f
                for f in findings
            ),
            findings,
        )
        findings, _ = self._run(
            {
                "logging_config.py": (
                    "from constellate.config import settings\n"
                    "from constellate.request_context import get_request_id\n"
                ),
                "api/request_id.py": "from constellate.request_context import set_request_id\n",
                "main.py": "from constellate.logging_config import configure_logging\n",
                "poll.py": "from constellate.logging_config import configure_logging\n",
            }
        )
        self.assertEqual(findings, [])

    def test_leaf_may_import_domain_and_another_leaf(self):
        """`domain/`'s rule, which the leaves take: usable by anything, importing none of
        the four. `domain/` is not one of the four, and neither is another leaf."""
        findings, _ = self._run(
            {
                "db.py": (
                    "from constellate.config import settings\n"
                    "from constellate.domain import events\n"
                ),
                "api/deps.py": "from constellate.db import get_session\n",
                "services/x.py": "from constellate.config import settings\n",
            }
        )
        self.assertFalse(any("db.py" in f for f in findings))

    # -- only logging_config.py may configure logging: the paired-run guard -----------------

    def test_logging_config_addhandler_is_not_violation(self):
        """logging_config.py is the one sanctioned module; its addHandler is not flagged.

        Run the same source twice: once as `logging_config.py`, where the exemption
        applies, and once under a different module name, where it must still be
        flagged. Without the second run, deleting the `key == LOG_CONFIG_OWNER` guard
        would leave this test passing -- the exemption would have nothing to prove it
        does anything.
        """
        fixture = """
            import logging, sys

            def configure():
                h = logging.StreamHandler(sys.stdout)
                logging.getLogger("x").addHandler(h)
            """
        exempt, _ = self._run({"logging_config.py": fixture})
        self.assertFalse(any("addHandler" in f for f in exempt))

        not_exempt, _ = self._run({"services/x.py": fixture})
        self.assertTrue(any("services/x.py" in f and "addHandler" in f for f in not_exempt))


if __name__ == "__main__":
    unittest.main()
