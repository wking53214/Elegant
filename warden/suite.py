"""Rule 7, the behavior-preservation gate: the target's own suite, before and after.

Elegant.md, Rule 7: "No beautification or fix commit merges without a green
automated suite." Until 2026-10-07 the tag team re-inspected with Ghost Tools
and attacked with the documentation-honesty oracle, and never ran the
target's tests. A transformation could therefore be ACCEPTED while breaking
the code it was beautifying. This module is the missing gate.

THE GATE

  before   the suite must run, collect at least one test, and be green.
           A suite that cannot protect behavior cannot license a change:
           "If the suite cannot protect invariants, add tests before
           changing behavior."
  after    no new failures or errors, and at least as many passes as before.

Anything else and the change is put back. The counts go into the notes so the
record says what was measured, not only the verdict.

WHAT IT RUNS

`python -m pytest -q -p no:cacheprovider` in the target's own directory, with
the target's own configuration. It only runs after a human has authorized a
write, because running a repository's tests runs that repository's code.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

#: pytest's exit code when it collected nothing.
_NO_TESTS = 5

_COUNT = re.compile(r"(\d+) (passed|failed|errors?|skipped|xfailed|xpassed)")


@dataclass(frozen=True)
class SuiteRun:
    """One run of a target's suite, as pytest reported it."""

    ran: bool
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    reason: str = ""
    #: Tests marked as expected to fail that did fail, and ones that passed anyway.
    xfailed: int = 0
    xpassed: int = 0

    @property
    def green(self) -> bool:
        return self.ran and self.passed > 0 and self.failed == 0 and self.errors == 0

    def describe(self) -> str:
        if not self.ran:
            return f"did not run ({self.reason})"
        return (f"{self.passed} passed, {self.failed} failed, {self.errors} errors, "
                f"{self.skipped} skipped, {self.xfailed} xfailed, {self.xpassed} xpassed")


def run_suite(target: Path, python: str, timeout: float = 900.0) -> SuiteRun:
    """Run the target's tests and read pytest's own summary.

    Bytecode goes to a fresh directory per run. Python trusts a cached .pyc
    whose source has the same size and the same mtime second, so an edit
    made within a second of the "before" run (VALUE = 1 -> VALUE = 2) was
    invisible to the "after" run and a breaking change passed the gate.
    Measured on this module's own test, 2 failures in 3 runs, before this.
    """
    with tempfile.TemporaryDirectory(prefix="warden-pyc-") as pyc:
        env = dict(os.environ, PYTHONPYCACHEPREFIX=pyc)
        try:
            done = subprocess.run(
                [python, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                cwd=str(target), capture_output=True, text=True, timeout=timeout, env=env,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return SuiteRun(ran=False, reason=f"pytest could not run: {exc}")
    if done.returncode == _NO_TESTS:
        return SuiteRun(ran=False, reason="pytest collected no tests")
    tail = "\n".join(done.stdout.strip().splitlines()[-3:])
    counts: Dict[str, int] = {}
    for number, kind in _COUNT.findall(tail):
        key = "errors" if kind.startswith("error") else kind
        counts[key] = counts.get(key, 0) + int(number)
    if not counts:
        reason = (done.stderr.strip().splitlines() or done.stdout.strip().splitlines()
                  or [f"exit {done.returncode}"])[-1]
        return SuiteRun(ran=False, reason=f"no pytest summary ({reason[:200]})")
    return SuiteRun(ran=True, passed=counts.get("passed", 0), failed=counts.get("failed", 0),
                    errors=counts.get("errors", 0), skipped=counts.get("skipped", 0),
                    xfailed=counts.get("xfailed", 0), xpassed=counts.get("xpassed", 0))


def preserved(before: SuiteRun, after: SuiteRun) -> Optional[str]:
    """None if behavior is preserved by Rule 7's standard, else why not."""
    if not after.ran:
        return f"the suite did not run after the change ({after.reason})"
    if after.failed or after.errors:
        return f"the change introduced failures ({after.describe()})"
    if after.passed < before.passed:
        return f"fewer tests pass after the change ({before.passed} -> {after.passed})"
    return None
