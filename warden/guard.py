"""The seams: what Warden checks about its own seat-fillers instead of trusting them.

Drafter "never writes", Ghost "reports only", Burnish "writes only through
Warden". Those are charters. Until now they were enforced by tests that read
each repo's imports, which proves nothing about what the code does when it
runs. Warden loads these seats by name into its own process, so it checks the
one thing it can see: did the tree change while a seat had control?

Also here: what an edit may touch (inside the target, inside the grant's
scope, outside the files that judge the work).
"""

from __future__ import annotations

import ast
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Dict, Iterator, Optional

from .authorization import Authorization
from .models import Transformation

_SKIP = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules", ".mypy_cache", ".ruff_cache"}
#: Past this many bytes in total the tree is fingerprinted but not restorable.
_RESTORE_LIMIT = 200 * 1024 * 1024

#: Prose a documentation grant may touch.
PROSE = {".md", ".rst", ".txt"}

#: The files that decide whether a change is acceptable. A proposer that can
#: edit them is grading its own work.
_PROTECTED_NAMES = {"conftest.py", "pytest.ini", "tox.ini", "setup.cfg", "pyproject.toml",
                    "noxfile.py", ".coveragerc", "Makefile"}
_PROTECTED_DIRS = {"tests", "test", ".github"}


class SeatBrokeCharter(RuntimeError):
    """A seat-filler changed the tree when its role does not allow it."""


def _walk(target: Path) -> Iterator[Path]:
    for path in sorted(Path(target).rglob("*")):
        if path.is_file() and not _SKIP.intersection(path.relative_to(target).parts):
            yield path


class Snapshot:
    """Every file under the target as it was, so a surprise can be named and undone."""

    def __init__(self, target: Path) -> None:
        self.target = Path(target)
        self.files: Dict[str, bytes] = {}
        self.restorable = True
        total = 0
        for path in _walk(self.target):
            data = path.read_bytes()
            total += len(data)
            self.restorable = self.restorable and total <= _RESTORE_LIMIT
            self.files[str(path.relative_to(self.target))] = data if self.restorable else b""
        if not self.restorable:
            self.files = {k: b"" for k in self.files}
        self._stat = self._stats()

    def _stats(self) -> Dict[str, tuple]:
        return {str(p.relative_to(self.target)): (p.stat().st_size, p.stat().st_mtime_ns)
                for p in _walk(self.target)}

    def changes(self) -> list[str]:
        now = self._stats()
        out = [f"added {k}" for k in now.keys() - self._stat.keys()]
        out += [f"removed {k}" for k in self._stat.keys() - now.keys()]
        for k in now.keys() & self._stat.keys():
            if now[k] != self._stat[k]:
                if self.restorable and (self.target / k).read_bytes() == self.files[k]:
                    continue  # touched but identical
                out.append(f"changed {k}")
        return sorted(out)

    def restore(self) -> None:
        if not self.restorable:
            return
        now = {str(p.relative_to(self.target)) for p in _walk(self.target)}
        for rel in now - self.files.keys():
            (self.target / rel).unlink(missing_ok=True)
        for rel, data in self.files.items():
            path = self.target / rel
            if not path.is_file() or path.read_bytes() != data:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)


@contextmanager
def watch(target: Path, who: str) -> Iterator[None]:
    """Run a seat that must not write. If it did, undo it and say so."""
    snap = Snapshot(target)
    yield
    changed = snap.changes()
    if changed:
        snap.restore()
        undone = "and undone" if snap.restorable else "and NOT undone (tree too large to restore)"
        raise SeatBrokeCharter(
            f"{who} changed the tree while it had control, which its role does not allow "
            f"({', '.join(changed[:5])}{'...' if len(changed) > 5 else ''}) {undone}.")


def inside(target: Path, rel: str) -> bool:
    candidate = Path(rel)
    if candidate.is_absolute():
        return False
    return (Path(target) / candidate).resolve().is_relative_to(Path(target).resolve())


def is_protected(rel: str) -> bool:
    parts = PurePosixPath(rel.replace("\\", "/")).parts
    name = parts[-1] if parts else ""
    return (name in _PROTECTED_NAMES or name.startswith("test_") or name.endswith("_test.py")
            or bool(_PROTECTED_DIRS.intersection(parts[:-1])))


def format_only(target: Path, edit) -> bool:
    """True when a Python edit changes no behavior: the syntax tree is identical.

    Comments and whitespace are not in the tree, so tidying them passes; any
    changed name, value, statement or docstring does not. This is what lets a
    finisher tidy a test file without being able to weaken it.
    """
    path = Path(target) / edit.path
    if path.suffix != ".py" or not path.is_file() or edit.kind not in {"write", "replace"}:
        return False
    old = path.read_text(encoding="utf-8")
    new = edit.new if edit.kind == "write" else old.replace(edit.old, edit.new, 1)
    try:
        return ast.dump(ast.parse(old)) == ast.dump(ast.parse(new))
    except SyntaxError:
        return False


def scope_allows(auth: Authorization, rel: str) -> bool:
    """A documentation grant covers prose only. "code" covers the rest."""
    if auth.scope.strip().lower() in {"code", "all"}:
        return True
    return Path(rel).suffix.lower() in PROSE


def violation(target: Path, proposal: Transformation, auth: Authorization) -> Optional[tuple[str, str]]:
    """(kind, why) when an edit may not be made, else None.

    kind is "escape" (outside the target: hostile or broken, stop everything) or
    "refused" (out of scope or a judging file: decline this one change).
    """
    for edit in proposal.edits:
        if not inside(target, edit.path):
            return "escape", f"edit path {edit.path!r} is outside the authorized target"
    for edit in proposal.edits:
        if is_protected(edit.path) and not format_only(target, edit):
            return "refused", (f"{edit.path} decides whether a change is acceptable (tests, test "
                               "configuration, CI); the loop may not edit it")
        if not scope_allows(auth, edit.path):
            return "refused", (f"{edit.path} is outside the grant's scope {auth.scope!r} "
                               "(a documentation grant covers prose only)")
    return None
