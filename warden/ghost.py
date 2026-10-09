"""Ghost Tools consumer.

Ghost Tools owns forensic truth. This module reads its JSON. It does not
re-implement detectors, ledgers, surgeons, or mutation.

If ghost_buster is importable, `scan()` will run a read-only mechanical
scan. If it is not, `load_findings()` still works on a JSON file produced
elsewhere. Absence of Ghost Tools is UNKNOWN, not a clean bill of health.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from .isolation import run_instrument
from .models import Defect, defects_from_ghost


def load_findings(path: Path) -> tuple[dict[str, Any], ...]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "findings" in raw:
        raw = raw["findings"]
    if isinstance(raw, list) and all(isinstance(f, dict) for f in raw):
        return tuple(raw)
    raise ValueError(f"{path}: not a Ghost Tools findings JSON (a list of records)")


def defects_from_file(path: Path) -> tuple[Defect, ...]:
    return defects_from_ghost(load_findings(path))


class Findings(tuple):
    """Ghost's findings, plus what Ghost said about how much it looked at.

    It is an ordinary tuple of findings. `blind` is a plain sentence when Ghost
    said it analysed nothing, so an empty list must not be read as clean; it is
    None when nothing was wrong or Ghost did not say.
    """

    blind: Optional[str] = None


DEFAULT_TIMEOUT = 600

_SCANNED = re.compile(r"scanning\s+(\d+)\s+file", re.IGNORECASE)
_NOTHING = re.compile(r"nothing\s+(was\s+)?analy[sz]ed|no\s+files?\s+(were\s+)?(scanned|analy[sz]ed)", re.IGNORECASE)


def _blind(stderr: str) -> Optional[str]:
    """A sentence if Ghost's stderr says it analysed nothing (Ghost prints 'scanning N file(s)')."""
    if _NOTHING.search(stderr):
        return "Ghost said it analysed nothing, so an empty list of findings does not mean the code is clean"
    counts = [int(n) for n in _SCANNED.findall(stderr)]
    if counts and counts[-1] == 0:
        return "Ghost scanned 0 files, so an empty list of findings does not mean the code is clean"
    return None


def scan(
    target: Path,
    *,
    ghost_tools_root: Optional[Path] = None,
    python: str = sys.executable,
    ghost_timeout: float = DEFAULT_TIMEOUT,
) -> tuple[dict[str, Any], ...]:
    """Read-only Ghost Tools scan. Does not operate, does not write a ledger.

    Returns the findings list (a `Findings`). Raises if the CLI cannot be run,
    does not finish within `ghost_timeout` seconds, or prints something that is
    not a list of findings. That is UNKNOWN-as-exception, not 'zero findings'.
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
    try:
        proc = run_instrument(cmd, roots=[ghost_tools_root], timeout=ghost_timeout)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"ghost_buster did not finish within {ghost_timeout:g} seconds") from exc
    if proc.returncode not in (0, 1) or not proc.stdout.strip():
        # ghost_buster uses 1 for 'findings exist'; 2 is usage.
        raise RuntimeError(
            f"ghost_buster failed ({proc.returncode}): {proc.stderr[-800:]}"
        )
    try:
        data = json.loads(proc.stdout)
    except ValueError as exc:
        raise RuntimeError("ghost_buster printed something that is not JSON") from exc
    if isinstance(data, dict) and "findings" in data:
        data = data["findings"]
    if not isinstance(data, list) or not all(isinstance(f, dict) for f in data):
        raise RuntimeError("ghost_buster JSON was not a list of findings")
    for f in data:
        if "id" in f and not isinstance(f["id"], str):
            raise RuntimeError("ghost_buster gave a finding whose id is not text")
    out = Findings(data)
    out.blind = _blind(proc.stderr) if not data else None
    return out


def finding_ids(findings: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    return tuple(str(f["id"]) for f in findings if f.get("id"))
