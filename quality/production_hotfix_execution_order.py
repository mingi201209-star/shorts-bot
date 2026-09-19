"""Traces the FULL set of `ci_*.py` files the production hotfix chain
actually executes -- not just the 47 files named in
`quality/production_hotfix_chain.py`.

Authority: this session's investigation (2026-09-19) found that
`PRODUCTION_HOTFIX_CHAIN` names only the hotfixes `main.yml` invokes
directly. Several of those files pull in further hotfixes as a side effect
of running, through three distinct mechanisms this module all traces:

1. A plain `import ci_x_hotfix` / `from ci_x_hotfix import name` at module
   scope (executes ci_x_hotfix.py's top-level code once, on first import).
2. `runpy.run_path("ci_x_hotfix.py", run_name="__main__")`.
3. `exec(compile(Path("ci_x_hotfix.py").read_text(...), ..., "exec"), ...)`.

`PRODUCTION_HOTFIX_CHAIN`'s own structural regression test
(`production_hotfix_chain_structure_regression_test.py`) only ever checked
the 47/48 it lists -- it has no visibility into hotfixes pulled in this
way, so a change to one of THOSE files was previously invisible to CI
change-detection on `ci_*.py` unless the change also happened to touch a
directly-listed file's own diff footprint.

This module computes the real, full execution order via static analysis
(no hotfix is actually run -- they mutate checked-in files, so tracing
them for real would corrupt the working tree). It is deliberately
conservative: it only follows references that name a `ci_*hotfix.py` file
outside of a comment line, which is how every hotfix in this repo chains
another one as of this writing.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Iterable, List, Set

ROOT = Path(__file__).resolve().parents[1]

#: Matches a quoted "ci_x_hotfix.py" literal, the shape used by both
#: `runpy.run_path(...)` and `Path("...").read_text()` / `exec(compile(...))`
#: chaining.
_QUOTED_HOTFIX_LITERAL = re.compile(r'["\'](ci_[A-Za-z0-9_]*hotfix)\.py["\']')

#: Matches the bare module name in `import ci_x_hotfix` / `from ci_x_hotfix
#: import ...`, the shape used by plain-import chaining.
_HOTFIX_MODULE_NAME = re.compile(r'^ci_.*hotfix$')


def direct_references(path: Path) -> List[str]:
    """Return the `ci_*.py` hotfix filenames `path` directly chains into,
    via any of the three mechanisms this module documents, deduplicated
    but otherwise unordered (order doesn't matter for the closure this
    module computes -- see its module docstring)."""
    text = path.read_text(encoding="utf-8")
    found: Set[str] = set()

    tree = ast.parse(text, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _HOTFIX_MODULE_NAME.match(alias.name):
                    found.add(alias.name + ".py")
        elif isinstance(node, ast.ImportFrom):
            if node.module and _HOTFIX_MODULE_NAME.match(node.module):
                found.add(node.module + ".py")

    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        for match in _QUOTED_HOTFIX_LITERAL.finditer(line):
            found.add(match.group(1) + ".py")

    found.discard(path.name)
    return sorted(found)


def _expand(entry: str, seen: Set[str], root: Path) -> List[str]:
    """Depth-first expansion of one chain entry's own execution, matching
    real Python import-cache semantics: within ONE entry's run (one
    `python <entry>` subprocess, per `apply_production_hotfix_chain.py`),
    a file referenced more than once only executes its top-level code the
    first time."""
    order: List[str] = []
    if entry in seen:
        return order
    path = root / entry
    if not path.is_file():
        return order
    seen.add(entry)
    order.append(entry)
    for child in direct_references(path):
        order.extend(_expand(child, seen, root))
    return order


def compute_execution_order(chain: Iterable[str], root: Path = ROOT) -> List[str]:
    """The full, ordered list of `ci_*.py` files executed when `chain` (in
    the shape of `PRODUCTION_HOTFIX_CHAIN`) is applied via
    `apply_production_hotfix_chain.py`.

    Each entry of `chain` is run as its own fresh subprocess (see
    `apply_production_hotfix_chain.py`), so entries that repeat --
    `ci_aviation_context_signature_compat_hotfix.py`'s documented
    intentional duplicate -- correctly re-expand and re-execute their own
    referenced children too; import caching only applies WITHIN one
    entry's own subprocess run, not across entries.
    """
    full: List[str] = []
    for entry in chain:
        full.extend(_expand(entry, set(), root))
    return full


def distinct_files(chain: Iterable[str], root: Path = ROOT) -> List[str]:
    """The distinct set of files `compute_execution_order` touches at
    least once, in first-seen order."""
    seen: List[str] = []
    seen_set: Set[str] = set()
    for name in compute_execution_order(chain, root):
        if name not in seen_set:
            seen_set.add(name)
            seen.append(name)
    return seen


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(ROOT))
    from quality.production_hotfix_chain import PRODUCTION_HOTFIX_CHAIN

    files = distinct_files(PRODUCTION_HOTFIX_CHAIN)
    listed = set(PRODUCTION_HOTFIX_CHAIN)
    hidden = [f for f in files if f not in listed]

    print(f"PRODUCTION_HOTFIX_CHAIN lists {len(listed)} distinct files.")
    print(f"The chain actually executes {len(files)} distinct files.")
    print(f"{len(hidden)} are executed only as a side effect of another entry:")
    for name in hidden:
        print(f"  {name}")
