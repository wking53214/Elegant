"""Warden governs its seats; it never depends on what sits in them."""

import ast
from pathlib import Path

import warden

_FORBIDDEN = {"burnish", "drafter", "ghost_buster", "swizzle", "assay"}


def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


def test_no_warden_module_imports_a_seat_filler():
    root = Path(warden.__file__).parent
    offenders = {str(p.relative_to(root)): sorted(_imports(p) & _FORBIDDEN)
                 for p in root.rglob("*.py") if _imports(p) & _FORBIDDEN}
    assert offenders == {}


def test_the_governor_holds_no_beautification_modules():
    root = Path(warden.__file__).parent
    moved = {"critic.py", "narrative.py", "readme.py", "drafters.py", "cns_boundary.py"}
    assert moved.isdisjoint({p.name for p in root.rglob("*.py")})
