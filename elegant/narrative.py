"""Architectural narrative extracted from the tree itself.

The README is a compilation of this narrative. Inventing a polished story
from the outside is a defect. This module only reports what the files
declare: module docstrings, pyproject scripts, test function counts,
CNS mentions, and whether a README already claims more than the tree
can support.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional


_TEST_FN = re.compile(r"^test_", re.M)
_CNS = re.compile(r"\b(?:from cns|import cns|cns\.gate|cns\.graph)\b")


@dataclass
class ModuleStory:
    path: str
    purpose: str
    classes: tuple[str, ...]
    functions: tuple[str, ...]
    cns_import: bool


@dataclass
class Narrative:
    root: str
    name: str
    version: Optional[str]
    description: Optional[str]
    scripts: tuple[tuple[str, str], ...]
    modules: tuple[ModuleStory, ...]
    test_functions: int
    test_files: tuple[str, ...]
    readme_exists: bool
    readme_text: str
    cns_mentioned: bool
    owns: tuple[str, ...]
    does_not_own: tuple[str, ...]
    unknowns: tuple[str, ...]
    claims_in_readme: tuple[str, ...]

    def test_count_claims(self) -> tuple[tuple[str, int], ...]:
        """Integers that a README/PROVENANCE presents as a test count."""
        text = self.readme_text
        found = []
        for m in re.finditer(
            r"(\d+)\s+tests?\s+(?:passed|pass|exist|in the|in this)",
            text,
            re.I,
        ):
            found.append((m.group(0), int(m.group(1))))
        for m in re.finditer(r"claims?\s+(\d+)\s+test", text, re.I):
            found.append((m.group(0), int(m.group(1))))
        return tuple(found)


def inspect_tree(root: Path) -> Narrative:
    root = Path(root).resolve()
    name = root.name
    version = None
    description = None
    scripts: list[tuple[str, str]] = []
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8", errors="replace")
        vm = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
        dm = re.search(r'^description\s*=\s*"([^"]+)"', text, re.M)
        nm = re.search(r'^name\s*=\s*"([^"]+)"', text, re.M)
        if vm:
            version = vm.group(1)
        if dm:
            description = dm.group(1)
        if nm:
            name = nm.group(1)
        for sm in re.finditer(r'^([A-Za-z0-9_-]+)\s*=\s*"([^"]+:[^"]+)"', text, re.M):
            scripts.append((sm.group(1), sm.group(2)))

    modules: list[ModuleStory] = []
    test_functions = 0
    test_files: list[str] = []
    cns_mentioned = False
    owns: list[str] = []
    does_not_own: list[str] = []
    unknowns: list[str] = []

    py_files = [p for p in root.rglob("*.py") if ".git" not in p.parts and "site-packages" not in p.parts]
    for p in sorted(py_files):
        rel = p.relative_to(root).as_posix()
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            unknowns.append(rel)
            continue
        if _CNS.search(src):
            cns_mentioned = True
        purpose = _module_purpose(src)
        classes, functions = _names(src)
        is_test = "test" in p.name.lower() or "/tests/" in f"/{rel.lower()}/" or "/Tests/" in f"/{rel}/"
        if is_test:
            n = _count_test_functions(src)
            if n:
                test_functions += n
                test_files.append(rel)
        modules.append(
            ModuleStory(
                path=rel,
                purpose=purpose,
                classes=classes,
                functions=functions,
                cns_import=bool(_CNS.search(src)),
            )
        )
        for line in src.splitlines()[:80]:
            s = line.strip()
            if s.upper().startswith("WHAT THIS OWNS") or s.upper().startswith("WHAT IT OWNS"):
                owns.append(rel)
            if "DOES NOT OWN" in s.upper() or "DOES NOT OWN" in s:
                does_not_own.append(rel)

    readme = _first_readme(root)
    readme_text = readme.read_text(encoding="utf-8", errors="replace") if readme else ""
    if _CNS.search(readme_text):
        cns_mentioned = True
    claims = tuple(
        line.strip()
        for line in readme_text.splitlines()
        if line.strip().startswith(("- ", "* ", "## "))
    )[:40]

    return Narrative(
        root=str(root),
        name=name,
        version=version,
        description=description,
        scripts=tuple(scripts),
        modules=tuple(modules),
        test_functions=test_functions,
        test_files=tuple(test_files),
        readme_exists=bool(readme),
        readme_text=readme_text,
        cns_mentioned=cns_mentioned,
        owns=tuple(owns),
        does_not_own=tuple(does_not_own),
        unknowns=tuple(unknowns),
        claims_in_readme=claims,
    )


def _first_readme(root: Path) -> Optional[Path]:
    for name in ("README.md", "Readme.md", "readme.md"):
        p = root / name
        if p.is_file():
            return p
    return None


def _module_purpose(src: str) -> str:
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return "(unparseable)"
    doc = ast.get_docstring(tree) or ""
    first = doc.strip().split("\n\n", 1)[0].strip().replace("\n", " ")
    return first[:400]


def _names(src: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return (), ()
    classes = tuple(
        n.name for n in tree.body if isinstance(n, ast.ClassDef)
    )
    functions = tuple(
        n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    return classes, functions


def _count_test_functions(src: str) -> int:
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return len(_TEST_FN.findall(src))
    n = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            n += 1
    return n
