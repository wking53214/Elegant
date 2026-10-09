"""SWIZZLE consumer: is the adversary's own instrument sound?

SWIZZLE owns adversarial challenge. Warden must not become SWIZZLE. What
Warden asks of it is one calibration question before it will write anything:
do SWIZZLE's own planted defects still all get proven? (`swizzle prove`).

The independent post-change oracle used to live here. It judges documentation,
which is a craft question, so it moved to Burnish with the rest of the
beautification. Warden now receives its verdict through `warden.craft`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


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


def governor_attacks(
    *,
    swizzle_root: Path,
    warden_root: Path,
    python: str = sys.executable,
) -> Optional[tuple[dict, ...]]:
    """SWIZZLE's report on attacks against this governor, or None if they could not run.

    Report only: each item says whether an invariant held. None is "not
    measured", and a caller must not read it as "no problems".
    """
    import json

    env = os.environ.copy()
    env["PYTHONPATH"] = str(swizzle_root) + os.pathsep + env.get("PYTHONPATH", "")
    try:
        proc = subprocess.run(
            [python, "-m", "swizzle.cli", "governor", "--warden", str(warden_root), "--json"],
            capture_output=True, text=True, env=env, timeout=900,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode not in (0, 1):
        return None
    try:
        items = json.loads(proc.stdout)
    except ValueError:
        return None
    if not items or any(i.get("status") == "not_run" for i in items):
        return None
    return tuple({"scenario": i["scenario"], "severity": i["severity"], "status": i["status"]} for i in items)


def assay_score(
    *,
    swizzle_root: Path,
    assay_root: Path,
    ghost_root: Optional[Path] = None,
    python: str = sys.executable,
) -> tuple[Optional[bool], dict, str]:
    """Ghost graded against ASSAY's answer key, by SWIZZLE's `assay` command.

    Returns (state, score, one-line summary). state is True when the key was
    proven and every specimen was scored, False when the key is unproven or
    something could not be scored (never read that as a pass), and None when
    the grading could not run at all. Warden only relays; the grading is
    SWIZZLE's and the answers are ASSAY's.
    """
    import json

    env = os.environ.copy()
    env["PYTHONPATH"] = str(swizzle_root) + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [python, "-m", "swizzle.cli", "assay", "--assay", str(assay_root), "--json"]
    if ghost_root is not None:
        cmd += ["--ghost-tools", str(ghost_root)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=600)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, {}, f"ASSAY grading could not run: {exc}"
    if proc.returncode == 2:
        why = (proc.stderr.strip().splitlines() or ["no reason given"])[-1]
        return False, {}, f"ASSAY grading failed (key unproven or specimen unscorable): {why}"
    if proc.returncode != 0:
        return None, {}, f"ASSAY grading exited {proc.returncode}"
    try:
        card = json.loads(proc.stdout)
        judgements = card["judgements"]
    except (ValueError, KeyError, TypeError):
        return None, {}, "ASSAY grading printed something unreadable"
    modes = [j for j in judgements if j.get("specimen_class") == "FAILURE_MODE"]
    score = {
        "key_proven": True,
        "failure_modes": len(modes),
        "caught": sum(j.get("outcome") == "banished" for j in modes),
        "escaped": sum(j.get("outcome") == "escaped" for j in modes),
        "misnamed": sum(j.get("outcome") == "misnamed" for j in modes),
        "proof": str(card.get("proof", "")),
    }
    return True, score, (f"ASSAY: Ghost caught {score['caught']} of {score['failure_modes']} "
                         f"known failure modes ({score['proof']})")
