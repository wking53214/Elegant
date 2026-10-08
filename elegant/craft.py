"""The seam between Elegant (who may change code) and a craft (who knows what better is).

Elegant owns the discipline of change: a human grant, a green suite before and
after, SWIZZLE's proofs, a record. It does not own the opinion about what makes
code beautiful. That opinion lives in a separate repository, Streamline, and
reaches Elegant through the four questions below.

THE FOUR QUESTIONS A CRAFT ANSWERS

  freeze   what is true of the tree right now, before anything is written?
  review   is the tree good enough yet, and in one sentence, why not?
  propose  what single change would make it better? (a proposal, never a write)
  attack   after the change, did the claim the change was meant to fix hold up?

Elegant asks them in that order and decides nothing the craft says on its own:
a craft's "good enough" cannot override a failed suite, a missing grant, or a
SWIZZLE proof that does not hold.

WHY A PROTOCOL AND NOT AN IMPORT

Elegant must be able to govern a craft it did not write, and a craft must not
be able to reach into the governor. Streamline imports Elegant. Elegant never
imports Streamline. The tests prove it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from .models import Defect, Transformation


@dataclass(frozen=True)
class AttackResult:
    """The post-change verdict of an oracle that is independent of the craft's reviewer."""

    judgement: str  # "ACCEPT" | "REJECT" | "INCONCLUSIVE"
    violations: tuple[str, ...]
    notes: str
    swizzle_prove: Optional[str] = None


@dataclass(frozen=True)
class Review:
    """A craft's reading of a tree: one verdict, and whether it is good enough."""

    good_enough: bool
    verdict: str


@runtime_checkable
class Ground(Protocol):
    """What a craft froze before the change. Elegant records only the fingerprint."""

    @property
    def fingerprint(self) -> str: ...


@runtime_checkable
class Craft(Protocol):
    """Everything Elegant needs from a repository that knows what better means."""

    def freeze(self, target: Path) -> Ground: ...

    def review(self, target: Path) -> Review: ...

    def propose(self, target: Path, observed: tuple[Defect, ...], ground: Ground) -> Transformation: ...

    def attack(self, target: Path, ground: Ground) -> AttackResult: ...
