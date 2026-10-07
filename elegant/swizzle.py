"""SWIZZLE consumer and a local independent oracle.

SWIZZLE owns adversarial challenge. Elegant must not become SWIZZLE, and
must not treat its own critic as an attack. The independent oracle here
freezes ground truth *before* a transformation and re-measures after.
It does not read Elegant's proposal to decide whether the proposal was
right — it reads the tree.

If the `swizzle` package is importable, `prove_self()` can run SWIZZLE's
own `prove` catalogue (SWIZZLE attacking *its* planted defects, not
certifying Elegant).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .narrative import inspect_tree


@dataclass(frozen=True)
class GroundTruth:
    """Frozen before anything Elegant writes."""

    test_functions: int
    module_count: int
    readme_sha16: str
    execute_present: bool


@dataclass(frozen=True)
class AttackResult:
    judgement: str  # "ACCEPT" | "REJECT" | "INCONCLUSIVE"
    violations: tuple[str, ...]
    notes: str
    swizzle_prove: Optional[str] = None


def freeze(root: Path) -> GroundTruth:
    nar = inspect_tree(root)
    readme = Path(nar.root) / "README.md"
    blob = readme.read_bytes() if readme.is_file() else b""
    import hashlib
    execute_present = any("execute" in m.functions or "execute" in m.classes for m in nar.modules)
    # also look at methods? skip — freeze what inspect_tree already knows
    for m in nar.modules:
        if m.path.endswith("pipeline.py") and "execute" in (m.purpose + "".join(m.functions)):
            execute_present = True
    return GroundTruth(
        test_functions=nar.test_functions,
        module_count=len(nar.modules),
        readme_sha16=hashlib.sha256(blob).hexdigest()[:16],
        execute_present=execute_present,
    )


def attack_documentation_honesty(root: Path, before: GroundTruth) -> AttackResult:
    """Independent of Elegant's critic. Re-counts the tree. Rejects a README
    that claims a test count the tree does not have.
    """
    after = inspect_tree(root)
    violations = []
    if after.test_functions != before.test_functions:
        # A documentation-only transform must not change the test suite.
        # If tests changed, this attack cannot attribute the README.
        return AttackResult(
            judgement="INCONCLUSIVE",
            violations=(),
            notes=(
                f"test_* count moved {before.test_functions} → {after.test_functions}; "
                "documentation-honesty oracle will not speak"
            ),
        )
    for phrase, n in after.test_count_claims():
        if n != after.test_functions:
            violations.append(
                f"README/PROVENANCE still claims {n} via {phrase!r}; "
                f"tree has {after.test_functions} test_* functions"
            )
    if violations:
        return AttackResult("REJECT", tuple(violations), "documentation honesty failed")
    return AttackResult("ACCEPT", (), "no false test-count claims remain")


def prove_self(
    *,
    swizzle_root: Optional[Path] = None,
    python: str = sys.executable,
) -> str:
    """Run SWIZZLE's own proofs. This does not certify Elegant."""
    env = os.environ.copy()
    if swizzle_root:
        env["PYTHONPATH"] = str(swizzle_root) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [python, "-m", "swizzle.cli", "prove"],
        capture_output=True,
        text=True,
        env=env,
        timeout=180,
    )
    return f"exit={proc.returncode}\n{proc.stdout[-1500:]}\n{proc.stderr[-500:]}"


def swizzle_proofs_hold(
    *,
    swizzle_root: Optional[Path] = None,
    python: str = sys.executable,
) -> tuple[bool, str]:
    """Whether SWIZZLE's own instrument is sound: every planted defect proven.

    This is a calibration check on the adversary, not a judgement of the
    target. An adversary whose proofs fail cannot back an ACCEPT. Returns
    (holds, one-line summary); a run that cannot start is (False, reason).
    """
    env = os.environ.copy()
    if swizzle_root:
        env["PYTHONPATH"] = str(swizzle_root) + os.pathsep + env.get("PYTHONPATH", "")
    try:
        proc = subprocess.run(
            [python, "-m", "swizzle.cli", "prove"],
            capture_output=True, text=True, env=env, timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"SWIZZLE proofs could not run: {exc}"
    lines = [ln for ln in proc.stdout.splitlines() if "proofs hold" in ln]
    summary = lines[-1].strip() if lines else (proc.stderr.strip().splitlines() or ["no output"])[-1]
    return proc.returncode == 0 and bool(lines), f"SWIZZLE proofs: {summary}"
