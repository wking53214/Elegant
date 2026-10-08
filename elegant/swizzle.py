"""SWIZZLE consumer: is the adversary's own instrument sound?

SWIZZLE owns adversarial challenge. Elegant must not become SWIZZLE. What
Elegant asks of it is one calibration question before it will write anything:
do SWIZZLE's own planted defects still all get proven? (`swizzle prove`).

The independent post-change oracle used to live here. It judges documentation,
which is a craft question, so it moved to Streamline with the rest of the
beautification. Elegant now receives its verdict through `elegant.craft`.
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
