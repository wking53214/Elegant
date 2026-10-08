"""The two seats Warden seats other repositories in.

Warden is the governor. It is the only thing that writes, and it decides when
the loop is done. It does not know what a good fix looks like, and it does not
know what beautiful code looks like. Two other repositories answer those:

  Drafter    in the loop. Looks at what Ghost found and proposes ONE change.
              A proposal is data. A Drafter never writes.
  Finisher    after the loop, once. Beautifies the converged code and writes
              the final README. Its output is also a proposal; Warden applies
              it under the same gate (grant, green suite, Ghost no worse).

Neither seat may decide that it is right. Warden checks the suite and Ghost
checks the result, so no one grades their own work.

Warden never imports the repositories that fill these seats; they import
Warden's data shapes. The tests prove it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from .models import Defect, Transformation
from .suite import SuiteRun


@dataclass(frozen=True)
class Facts:
    """What Warden and Ghost measured at the converged state, handed to the Finisher.

    The Finisher counts and detects nothing itself. If it states a test result
    or a remaining problem, it is quoting this.
    """

    #: The target's own suite, run by Warden after the loop. None: it was not run.
    suite: Optional[SuiteRun]
    #: What Ghost still reports. Converged means no proposals are left, not that this is empty.
    remaining: tuple[Defect, ...]
    #: How many loop cycles ran.
    cycles: int


@runtime_checkable
class Drafter(Protocol):
    """Called once per loop cycle. Returns None when it has nothing left to propose."""

    def propose(self, target: Path, observed: tuple[Defect, ...], baseline: str) -> Optional[Transformation]: ...


@runtime_checkable
class Finisher(Protocol):
    """Called once, after the loop has converged. Returns None if nothing to finish."""

    def finish(self, target: Path, baseline: str, facts: Facts) -> Optional[Transformation]: ...
