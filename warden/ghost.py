"""Ghost Tools consumer.

Ghost Tools owns forensic truth. This module reads its JSON. It does not
re-implement detectors, ledgers, surgeons, or mutation.

If ghost_buster is importable, `scan()` will run a read-only mechanical
scan. If it is not, `load_findings()` still works on a JSON file produced
elsewhere. Absence of Ghost Tools is UNKNOWN, not a clean bill of health.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from .isolation import run_instrument
from .models import Defect, defects_from_ghost


def load_findings(path: Path) -> tuple[dict[str, Any], ...]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return tuple(raw)
    if isinstance(raw, dict) and "findings" in raw:
        return tuple(raw["findings"])
    raise ValueError(f"{path}: not a Ghost Tools findings JSON")


def defects_from_file(path: Path) -> tuple[Defect, ...]:
    return defects_from_ghost(load_findings(path))


def scan(
    target: Path,
    *,
    ghost_tools_root: Optional[Path] = None,
    python: str = sys.executable,
) -> tuple[dict[str, Any], ...]:
    """Read-only Ghost Tools scan. Does not operate, does not write a ledger.

    Returns the findings list. Raises FileNotFoundError if the CLI cannot
    be located. That is UNKNOWN-as-exception, not 'zero findings'.
    """
    target = Path(target).resolve()
    cmd = [
        python,
        "-m",
        "ghost_buster.cli",
        str(target),
        "--json",
        "--single-repo",
        "--no-tests",
        "--no-secrets",
        "--no-ledger",
        "--no-structure",
        "--no-project",
        "--no-correlate",
    ]
    proc = run_instrument(cmd, roots=[ghost_tools_root], timeout=1800)
    if proc.returncode not in (0, 1) or not proc.stdout.strip():
        # ghost_buster uses 1 for 'findings exist'; 2 is usage.
        raise RuntimeError(
            f"ghost_buster failed ({proc.returncode}): {proc.stderr[-800:]}"
        )
    data = json.loads(proc.stdout)
    if isinstance(data, dict) and "findings" in data:
        data = data["findings"]
    if isinstance(data, list) and all(isinstance(f, dict) for f in data):
        return tuple(data)
    raise RuntimeError("ghost_buster JSON was not a findings list")


def finding_ids(findings: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    return tuple(str(f["id"]) for f in findings if f.get("id"))
