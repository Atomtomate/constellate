"""Check the layering under `api/src/constellate/`: what each module may import, query and log.

Five questions a review would otherwise answer by reading every import in the package:

- do imports point the documented way -- `api/` -> `services/` -> `repos/` -> `models/`,
  with `domain/` usable by any of them and itself importing none, and a leaf outside the
  layers under that same rule (`leaf_importers` says which modules are leaves)?
- does a module in `api/` reach `repos/` past `services/`?
- is `sources/` reached only through the interface `services/` declares -- no layer and no
  leaf imports a module of it, and an adapter imports only `domain/`, its own package and
  the leaves?
- does anything outside `repos/` build or run SQL?
- does anything other than `logging_config.py` configure logging handlers or levels?

The rules are `docs/03-architecture.md`'s -- "Layers inside the API package", and the
Conventions' "Health" for the one sanctioned query; this only answers them the same way
every run. Reports; never fixes. Outside the layers a module is a leaf or an entry point,
those two kinds and no third, and which is derived from what reaches it rather than listed:
`main.py` and `poll.py` are reached by nothing and sit above `api/`, free to reach down;
everything anything imports is a leaf and held to a leaf's rule, a module only the entry
points import included -- so `logging_config.py` may reach `domain/` and the other leaves,
never a layer. The day something imports an entry point it becomes a leaf the same way.

A line carrying `allowed:` is a sanctioned exception, printed with what sanctions it so it
stays visible and a *new* one of the same shape still shows up as a violation. Every other
line is a violation. The exit status is 1 when there is at least one violation.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

import report

DEFAULT_ROOT = Path(__file__).resolve().parent.parent / "api" / "src" / "constellate"

PACKAGE = "constellate"
LAYERS = ("api", "services", "repos", "models")
DOMAIN = "domain"
SOURCES = "sources"
#: The directories the placement rules are written against: the four layers, `domain/`,
#: which any of them may use, and `sources/`, which none of them may. Anything else in the
#: package is a leaf or an entry point, and `leaf_importers` says which.
PLACED = (*LAYERS, DOMAIN, SOURCES)

LAYERING_DOC = "docs/03-architecture.md"

# Only `api/` -> `repos/` counts as a skipped layer. Every layer above `models/` names the
# ORM classes in its own signatures, and the layering document calls exactly one import a
# skip: "A router that imports from `repos/` has skipped a layer". Counting `-> models/` as
# one too would report the package's ordinary vocabulary as a violation on every run.
#
# No sanctioned skips. The sibling's check carried a list of routers with no logic to put in
# a service; this package has none, and the first router that earns one brings the list
# back with the rule that sanctions it, rather than an empty table waiting here.

#: SQLAlchemy names whose call builds a query. `func`, `and_`, `case` and the column types
#: are deliberately absent: `models/` builds tables out of them, which is its job.
SQL_CONSTRUCTORS = frozenset(
    {"select", "insert", "update", "delete", "text", "union", "union_all", "exists"}
)
#: Names imported directly off `sqlalchemy` that are themselves a submodule, not a
#: constructor -- `from sqlalchemy import sql` binds the submodule the same way `import
#: sqlalchemy.sql as sq` binds it by path, so `sql.select(...)` is exactly as much a build
#: as `sq.select(...)` or `sa.select(...)`. Not every non-constructor name imported from
#: `sqlalchemy` belongs here -- `Integer`, `func`, `and_`, `case`, `or_` are symbols, not
#: submodules, and treating them the same way would chase attribute calls that are not SQL
#: at all.
SQLALCHEMY_SUBMODULES = frozenset({"sql"})
#: Methods that run one. `add`, `flush` and `commit` are absent on purpose -- the write
#: commits in the service that completes it (`db.get_session` says why), so they are not
#: repos-only and flagging them would contradict a rule this script also enforces.
SQL_EXECUTORS = frozenset({"execute", "scalar", "scalars", "query"})
#: `session.get(pk)` is a primary-key SELECT and belongs in `repos/` like any other, but
#: `.get` is also `dict.get` and a hundred unrelated methods -- so unlike the executors
#: above it counts only when its receiver is a `Session`. It is narrowed by the receiver's
#: annotation, which is why it keys on a bare-name annotation and a non-bare one
#: (`orm.Session`) slips through. `SessionDep` is listed by name rather than resolved: every
#: router and dependency in `api/` writes `session: SessionDep` (`api/deps.py`'s
#: `SessionDep = Annotated[Session, Depends(...)]`), never the bare `Session` this script
#: would otherwise need to trace the alias to find.
SESSION_TYPES = frozenset({"Session", "SessionDep"})
SQL_RULE = "repos/ is the only module that knows SQL"
#: Modules outside the layers are not exempt from it. `db.py` is the near miss worth
#: naming: it owns the engine and the `Session` factory, which every query needs and neither
#: of which is a query, so it is silent here rather than excused.

#: `(file, exact statement text) -> reason`: keyed on the statement, not the file, so a
#: *different* SQL line in `health.py` still shows up as a violation -- the sanction is for
#: `select 1`, the readiness probe, not a blanket pass for anything the file happens to run
#: later. `ast.walk` visits the constructor call (`text('select 1')`) and the executor call
#: around it (`session.execute(text('select 1'))`) as two separate nodes, so both need an
#: entry.
_HEALTH_READY_REASON = (
    f"{LAYERING_DOC} (Conventions, Health): `select 1` is a readiness probe, not a query"
)
SQL_SANCTIONED: dict[tuple[str, str], str] = {
    ("api/routers/health.py", "text('select 1')"): _HEALTH_READY_REASON,
    ("api/routers/health.py", "session.execute(text('select 1'))"): _HEALTH_READY_REASON,
}
#: `models/` may build a table expression with `text()` -- `server_default=sa.text(...)` on
#: a `mapped_column` is the standard idiom for a table default -- but never runs a query.
#: Narrower than the general SQL_SANCTIONED mapping above because it is not one statement:
#: any `text(...)` call in `models/` is sanctioned, not just a specific literal. Every other
#: constructor (`select`, `insert`, ...) in `models/` stays a violation like anywhere else.
MODELS_TEXT_SANCTION = (
    "models/ builds table expressions, a text() default among them; it never runs a query"
)


def module_key(package_root: Path, path: Path) -> str:
    """The module's path inside the package, e.g. `api/routers/health.py`, as printed."""
    return path.relative_to(package_root).as_posix()


def package_of(key: str) -> str:
    """The dotted package a module file lives in, for resolving its relative imports."""
    return ".".join([PACKAGE, *key.split("/")[:-1]])


def _is_none_literal(node: ast.expr) -> bool:
    """Is this `None`, spelled as a constant?"""
    return isinstance(node, ast.Constant) and node.value is None


def _annotation_base(annotation: ast.expr | None) -> str | None:
    """The base name of an annotation, past a subscript, a union, or `Optional`.

    `dict[str, Any]` resolves to `dict`, a subscript resolving to its own value's name
    only, never further in -- `Annotated[Session, ...]` is `Annotated`, not `Session`, so
    an alias's own definition line does not retroactively make every value annotated
    `Annotated[Session, ...]` read as a `Session`. (`SessionDep` is recognised as its own
    name where it is used, not resolved through this -- see `SESSION_TYPES`.)

    `X | None` (PEP 604) and `Optional[X]` both resolve to `X`'s own base name: an optional
    session is still a session for `.get(...)`'s purposes. `None | None` and a union of two
    real types (neither arm `None`) resolve to nothing -- there is no single base to report.

    A string annotation (a forward reference) resolves to nothing; rare enough here not to
    chase.
    """
    if isinstance(annotation, ast.Name):
        return annotation.id
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        if _is_none_literal(annotation.right):
            return _annotation_base(annotation.left)
        if _is_none_literal(annotation.left):
            return _annotation_base(annotation.right)
        return None
    if isinstance(annotation, ast.Subscript) and isinstance(annotation.value, ast.Name):
        if annotation.value.id == "Optional":
            return _annotation_base(annotation.slice)
        return annotation.value.id
    return None


def annotations_in_scope(tree: ast.Module) -> dict[int, dict[str, str]]:
    """For each node, the annotated names visible in its innermost enclosing function.

    Resolution has to be per scope rather than per module: `api/errors.py` binds `exc`
    several times, to different exception types, in sibling handlers. A module-wide map
    either guesses or gives up, and both answers are wrong.

    Bare-name and subscripted annotations are recorded, on parameters and annotated
    assignments, resolved to their base name (`_annotation_base`). That is enough to say
    what a value *is*, which is what the `session.get` narrowing turns on. `ast.walk` is
    breadth-first, so an outer function is visited before the functions nested in it and
    the innermost binding is the one left standing.
    """
    scopes: dict[int, dict[str, str]] = {}
    for func in ast.walk(tree):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        args = func.args
        names: dict[str, str] = {}
        for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs, args.vararg, args.kwarg):
            base = _annotation_base(arg.annotation) if arg is not None else None
            if base is not None:
                names[arg.arg] = base
        for node in ast.walk(func):
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                base = _annotation_base(node.annotation)
                if base is not None:
                    names[node.target.id] = base
        for node in ast.walk(func):
            scopes[id(node)] = names
    return scopes


def is_placed(head: str) -> bool:
    """One of the six the placement rules are written against: a layer, `domain/`, `sources/`."""
    return head in PLACED


def file_layer(key: str) -> str | None:
    """The placed directory a module file belongs to, or None for a module outside them."""
    head = key.split("/")[0]
    return head if is_placed(head) else None


def import_layer(module: str) -> str | None:
    """The placed directory a dotted import names, or None when it points outside them."""
    parts = module.split(".")
    if len(parts) < 2 or parts[0] != PACKAGE:
        return None
    return parts[1] if is_placed(parts[1]) else None


def outside_unit(key: str) -> str | None:
    """The unit a file outside the placed directories belongs to, as an import names it.

    `db.py` -> `db`, `api/deps.py` -> None. Spelled so a file key and a dotted import
    resolve to the same string, which is what lets one be looked up by the other.
    """
    if file_layer(key) is not None:
        return None
    return key.split("/")[0].removesuffix(".py")


def import_unit(module: str) -> str | None:
    """The same unit a dotted import names; None for a placed directory or a foreign module."""
    parts = module.split(".")
    if len(parts) < 2 or parts[0] != PACKAGE:
        return None
    return None if is_placed(parts[1]) else parts[1]


#: The package root, a leaf by construction: every import of anything in the package runs
#: `__init__.py` first, and no module ever spells `from constellate.__init__ import ...`, so
#: waiting for an import to name it would leave the one file every layer executes free to
#: import any of them. A re-export added there -- the ordinary reason an `__init__.py` stops
#: being empty -- would have `models/` load `services/` at import time.
PACKAGE_ROOT_UNIT = "__init__"


def leaf_importers(entries_by_key: dict[str, list]) -> dict[str, str]:
    """Each leaf outside the placed directories, and why it is one: what in the package imports it.

    A module outside the four layers, `domain/` and `sources/` is one of two kinds, and
    which one is derivable rather than listed. A **leaf** is reached by something in the
    package -- `ids.py` because `models/base.py` reaches for `uuid7`, `db.py` because
    `api/deps.py` reaches for `get_session`, `logging_config.py` because `main.py` and
    `poll.py` reach for `configure_logging` -- so it sits under whatever reaches it and
    takes `domain/`'s rule: usable by anything, importing none of the four and no adapter.
    An **entry point** (`main.py`, `poll.py`) is reached by nothing and sits above `api/`,
    reaching down into the layers and handing a service its adapter, which is the chain
    rather than a breach of it.

    Reached by anything, the entry points included -- `docs/03`'s "nothing imports an entry
    point" read from the other end. A module only `poll.py` imports is below `poll.py`,
    which is above `api/`, so there is no position for it but a leaf's; a third kind, below
    an entry point yet free to reach a layer, would be the opening through which the
    poller's helper loads `api/` to write one log line. With every module a reacher, one
    pass over the package is the whole closure: what a leaf imports is reached by that leaf
    directly, so a module imported solely by `config.py` is a leaf with no second hop.

    `sources/` reaches too: a helper only an adapter imports is under the adapter, and an
    adapter may import only `domain/` and the leaves, so the helper has to be one -- held
    to the leaf's rule, which keeps it from reaching a layer the adapter may not.

    Derived from the package because a listed set would go stale silently: the next leaf
    added would default to "entry point" and go unchecked. The reason comes back with each
    leaf so a finding can name what makes the module one, and the first reacher in sorted
    order wins -- there may be several, and one is enough to prove the direction.
    """
    leaves: dict[str, str] = {}
    if any(outside_unit(key) == PACKAGE_ROOT_UNIT for key in entries_by_key):
        leaves[PACKAGE_ROOT_UNIT] = "every import of the package runs it"
    for key in sorted(entries_by_key):
        for _lineno, module, _names in entries_by_key[key]:
            unit = import_unit(module)
            if unit is not None and unit not in leaves:
                leaves[unit] = f"{key} imports it"
    return leaves


def imported(tree: ast.Module, package: str) -> list[tuple[int, str, list[tuple[str | None, str]]]]:
    """Every import as (line, dotted module, [(name imported, name bound)]).

    A plain ``import a.b`` reports its name as None: nothing inside the module was named,
    only the module itself. Relative forms are resolved against ``package``, so no caller
    has to know it was written relatively.
    """
    found: list[tuple[int, str, list[tuple[str | None, str]]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound = alias.asname or alias.name.split(".")[0]
                found.append((node.lineno, alias.name, [(None, bound)]))
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                parts = package.split(".")
                base = parts[: max(len(parts) - node.level + 1, 0)]
                module = ".".join([*base, node.module] if node.module else base)
            else:
                module = node.module or ""
            if module == PACKAGE:
                # `from constellate import repos` names the layer in the alias, not in the
                # module, so reporting it as an import of `constellate` hides it from every
                # check that keys on the module. Rewrite it to the form those checks read.
                # Compared against PACKAGE, not `package`: the argument is the *importing*
                # module's own package, which is what relative levels resolve against.
                found.extend(
                    (node.lineno, f"{PACKAGE}.{a.name}", [(None, a.asname or a.name)])
                    for a in node.names
                )
            else:
                found.append(
                    (node.lineno, module, [(a.name, a.asname or a.name) for a in node.names])
                )
    return found


def check_direction(key: str, entries: list, leaves: dict[str, str]) -> list[str]:
    """Imports point down `api/` -> `services/` -> `repos/` -> `models/`; `domain/` imports none;
    `sources/` is reached by no layer and reaches only `domain/` and the leaves.

    A module *importing* `domain/` stays fine -- that is what "usable by anything" means, so
    `domain/` only drops out of the target side, never the source side. `sources/` is the
    mirror image: it drops out of the *target* side for every layer and every leaf, because
    a service reaches an adapter only through the interface it declares and an entry point
    hands it the concrete one -- and on the source side it may name `domain/`, its own
    package and the leaves, nothing else.

    A module outside the placed directories is placed by `leaves`, not exempted: in it is a
    leaf, reaching upward and in violation; absent is an entry point above `api/`, reaching
    downward and fine. Which is which is `leaf_importers`' to say.
    """
    layer = file_layer(key)
    unit = outside_unit(key)
    leaf_reason = leaves.get(unit) if unit is not None else None
    findings: list[str] = []
    for lineno, module, _names in entries:
        target = import_layer(module)
        if target is None or target == DOMAIN or target == layer:
            continue
        if layer == DOMAIN:
            findings.append(
                f"{key}:{lineno}: domain/ imports {target}/, but domain/ is usable by "
                "anything and uses nothing -- the middle layers know nothing about SQL, "
                "and the ORM is the database's shape"
            )
        elif target == SOURCES:
            if layer is not None:
                findings.append(
                    f"{key}:{lineno}: {layer}/ imports sources/, but no layer does -- a "
                    "service reaches an adapter only through the interface it declares "
                    f"(services/sources.py), and an entry point hands it the concrete one "
                    f"({LAYERING_DOC})"
                )
            elif leaf_reason is not None:
                findings.append(
                    f"{key}:{lineno}: imports sources/, but {leaf_reason} -- a leaf is "
                    "usable by any layer, which would then reach the adapter through it"
                )
        elif layer == SOURCES:
            findings.append(
                f"{key}:{lineno}: sources/ imports {target}/, but a source imports only "
                "domain/ and the leaves -- it knows an external API or a file format, "
                f"never SQL ({LAYERING_DOC})"
            )
        elif layer is None:
            if leaf_reason is not None:
                findings.append(
                    f"{key}:{lineno}: imports {target}/, but {leaf_reason} -- a leaf is "
                    "usable by anything and imports none of the four"
                )
        elif LAYERS.index(target) < LAYERS.index(layer):
            findings.append(
                f"{key}:{lineno}: {layer}/ imports {target}/, against "
                "api/ -> services/ -> repos/ -> models/"
            )
    return findings


def check_skips(entries_by_key: dict[str, list]) -> list[str]:
    """Which `api/` modules reach `repos/` past `services/`: every one is a finding.

    One line per module, at its first `repos/` import: the finding is that the module
    skips, not how many times.
    """
    findings: list[str] = []
    for key, entries in sorted(entries_by_key.items()):
        if file_layer(key) != "api":
            continue
        repos_lines = [
            lineno for lineno, module, _names in entries if import_layer(module) == "repos"
        ]
        if repos_lines:
            findings.append(
                f"{key}:{min(repos_lines)}: imports repos/, skipping services/ -- a router "
                f"that imports from repos/ has skipped a layer ({LAYERING_DOC})"
            )
    return findings


def check_sql(
    key: str, tree: ast.Module, entries: list, scopes: dict[int, dict[str, str]]
) -> tuple[list[str], list[str]]:
    """SQL is built and run in `repos/` only; one finding (or sanctioned line) per statement."""
    if file_layer(key) == "repos":
        return [], []
    building_tables = file_layer(key) == "models"
    constructors = {
        bound
        for _lineno, module, names in entries
        if module == "sqlalchemy" or module.startswith("sqlalchemy.")
        for name, bound in names
        if name in SQL_CONSTRUCTORS
    }
    # `import sqlalchemy as sa` binds the module, not a constructor, so `sa.select(...)` is
    # an attribute call that no name in `constructors` matches. Track the module's own
    # aliases -- by import path (`import sqlalchemy.sql as sq`, `module` dotted) or by name
    # (`from sqlalchemy import sql`, `SQLALCHEMY_SUBMODULES`) -- and count
    # `<alias>.<constructor>(...)` as a build too.
    sqla_modules = {
        bound
        for _lineno, module, names in entries
        if module == "sqlalchemy" or module.startswith("sqlalchemy.")
        for name, bound in names
        if name is None or name in SQLALCHEMY_SUBMODULES
    }
    violations: dict[str, set[int]] = {}
    allowed: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        shape: str | None = None
        constructor_name: str | None = None
        if isinstance(func, ast.Name) and func.id in constructors:
            shape = f"{func.id}("
            constructor_name = func.id
        elif isinstance(func, ast.Attribute):
            recv = func.value
            if (
                isinstance(recv, ast.Name)
                and recv.id in sqla_modules
                and func.attr in SQL_CONSTRUCTORS
            ):
                shape = f"{recv.id}.{func.attr}("
                constructor_name = func.attr
            elif func.attr in SQL_EXECUTORS:
                shape = f".{func.attr}("
            elif (
                func.attr == "get"
                and isinstance(recv, ast.Name)
                and scopes.get(id(node), {}).get(recv.id) in SESSION_TYPES
            ):
                shape = ".get("
        if shape is None:
            continue
        # `models/` may build a table expression out of `text()` -- see MODELS_TEXT_SANCTION
        # -- for any statement, not just one literal, so this checks the constructor's own
        # name rather than looking the statement up in SQL_SANCTIONED.
        if building_tables and constructor_name == "text":
            sanctioned = f"{key}:{node.lineno}: {ast.unparse(node)} — {MODELS_TEXT_SANCTION}"
            allowed.append((node.lineno, sanctioned))
            continue
        stmt = ast.unparse(node)
        sanction = SQL_SANCTIONED.get((key, stmt))
        if sanction:
            allowed.append((node.lineno, f"{key}:{node.lineno}: {stmt} — {sanction}"))
        else:
            violations.setdefault(shape, set()).add(node.lineno)
    findings: list[str] = []
    if violations:
        where = "; ".join(
            f"{call} at {', '.join(str(n) for n in sorted(at))}"
            for call, at in sorted(violations.items())
        )
        # "Why is this one not exempt?" is the first question a finding here raises, and
        # belonging to no layer is the whole answer -- which the layer lookup already knows.
        named = key if file_layer(key) else f"{key} (outside the layers)"
        findings.append(f"{named}: {where} — {SQL_RULE}")
    return findings, [text for _lineno, text in sorted(allowed)]


LOG_CONFIG_OWNER = "logging_config.py"
LOG_CONFIG_RULE = (
    "logging_config.py is the only module that may configure logging handlers or levels"
)

#: See `check_logging_cfg`'s docstring for why these are matched by name alone.
LOG_CONFIG_CALLS = frozenset(
    {"addHandler", "removeHandler", "setLevel", "basicConfig", "dictConfig", "fileConfig"}
)

LOG_CONFIG_ATTRS = frozenset({"handlers", "propagate"})


def check_logging_cfg(key: str, tree: ast.Module) -> list[str]:
    """Only ``logging_config.py`` may configure logging handlers or levels.

    Three forms, each matched by name alone rather than by narrowing to a known logger
    or import binding: a call to `LOG_CONFIG_CALLS`; an import of one of them from
    ``logging[.config]``, flagged at the import regardless of the alias it binds to; any
    use -- read, write, call or subscript -- of a `.handlers` or `.propagate` attribute.
    Narrowing the receiver would miss a chained ``logging.getLogger(...).addHandler(...)``,
    ``logging.root`` and ``self.log`` -- the false positive accepted in exchange is an
    unrelated same-named method or attribute.
    """
    if key == LOG_CONFIG_OWNER:
        return []

    findings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            if name in LOG_CONFIG_CALLS:
                findings.append(f"{key}:{node.lineno}: calls {name}() — {LOG_CONFIG_RULE}")
        elif isinstance(node, ast.ImportFrom) and node.module in ("logging", "logging.config"):
            for alias in node.names:
                if alias.name in LOG_CONFIG_CALLS:
                    findings.append(
                        f"{key}:{node.lineno}: imports {alias.name} from {node.module} "
                        f"— {LOG_CONFIG_RULE}"
                    )
        elif isinstance(node, ast.Attribute) and node.attr in LOG_CONFIG_ATTRS:
            findings.append(f"{key}:{node.lineno}: uses {node.attr} — {LOG_CONFIG_RULE}")

    return findings


def check(package_root: Path) -> tuple[list[str], list[str], int]:
    """Every check over the package: (violations, sanctioned exceptions, modules read)."""
    findings: list[str] = []
    exceptions: list[str] = []
    entries_by_key: dict[str, list] = {}
    trees: dict[str, ast.Module] = {}

    for path in sorted(package_root.rglob("*.py")):
        key = module_key(package_root, path)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except SyntaxError as exc:
            findings.append(f"{key}:{exc.lineno}: will not parse ({exc.msg})")
            continue
        trees[key] = tree
        entries_by_key[key] = imported(tree, package_of(key))

    # The `session.get` narrowing keys on parameter annotations, so build the per-node
    # scope map once here rather than once per module.
    scopes_by_key = {key: annotations_in_scope(tree) for key, tree in trees.items()}

    # Which modules outside the layers are leaves is a property of the whole package, so it
    # is derived once here rather than per module.
    leaves = leaf_importers(entries_by_key)

    for key in sorted(trees):
        findings += check_direction(key, entries_by_key[key], leaves)
    findings += check_skips(entries_by_key)
    for key in sorted(trees):
        found, allowed = check_sql(key, trees[key], entries_by_key[key], scopes_by_key[key])
        findings += found
        exceptions += allowed
    for key in sorted(trees):
        findings += check_logging_cfg(key, trees[key])
    return findings, exceptions, len(trees)


def main() -> int:
    """Parse arguments, run every check and print the violations and the exceptions."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("package_root", nargs="?", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.package_root.resolve()
    if not root.is_dir():
        return report.abort("layering", f"no package at {root}")
    findings, exceptions, modules = check(root)
    # The sanctioned exceptions first, so the violations sit next to the count that ends the
    # run rather than above a list the reader has already accepted.
    for allowed in exceptions:
        print(f"layering: allowed: {allowed}")
    return report.verdict(
        "layering",
        findings,
        failed=(
            f"{len(findings)} violation(s) and {len(exceptions)} sanctioned exception(s) "
            f"across {modules} module(s)"
        ),
        consistent=(
            f"{modules} module(s); imports point down, no layer skip, sources/ reached only "
            f"through services/sources.py, SQL stays in repos/, logging configured in "
            f"{LOG_CONFIG_OWNER} ({len(exceptions)} sanctioned exception(s))"
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
