"""The deletion gate: code is removed only after two loop validations.

WHY

A suite that stays green does not prove deleted code was unused. On CNS,
three of four "unused" findings were pytest hooks that the framework calls by
name; deleting them would have passed the tests and silently dropped an
enforcement rule. Deletion is the one change a green suite cannot vouch for,
so it must survive more scrutiny than any other.

THE RULE

A proposal that removes code is HELD, not applied, until the same removal has
passed two separate validations, each on its own cycle of the loop. A
validation is one full pass, measured fresh:

    SWIZZLE's proofs hold            (the instrument is still calibrated)
    the target's suite is green      (Rule 7, on the tree as it stands)
    Ghost re-observes, and still reports the findings the removal answers
    the same removal is proposed against the same text
    the suite counts match the previous validation

Any change resets the count to one. The second validation is followed
immediately by the application, which runs the usual before and after suite
gate and puts the change back on failure. Warden cannot be configured to skip
this gate: without Ghost, a suite, or SWIZZLE not failing, nothing is deleted.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .models import Transformation

#: Validations required before a removal is applied.
REQUIRED_VALIDATIONS = 2

_PROSE = {".md", ".rst", ".txt"}


def _lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def is_deletion(target: Path, proposal: Transformation) -> bool:
    """True when any edit takes code away: a delete, or a code file that shrinks."""
    target = Path(target)
    for edit in proposal.edits:
        if edit.kind == "delete":
            return True
        if Path(edit.path).suffix.lower() in _PROSE:
            continue
        if edit.kind == "replace" and _lines(edit.old) > _lines(edit.new):
            return True
        if edit.kind == "write":
            path = target / edit.path
            if path.is_file() and _lines(path.read_text(encoding="utf-8")) > _lines(edit.new):
                return True
    return False


@dataclass
class _Record:
    key: str
    counts: tuple[int, int, int]
    validations: int


class DeletionGate:
    """Counts consecutive matching validations of one pending removal."""

    def __init__(self, required: int = REQUIRED_VALIDATIONS) -> None:
        self.required = required
        self._record: Optional[_Record] = None

    def validations(self, key: str) -> int:
        return self._record.validations if self._record and self._record.key == key else 0

    def record(self, key: str, counts: tuple[int, int, int]) -> int:
        """Log one passed validation; return how many in a row now stand."""
        prior = self._record
        if prior and prior.key == key and prior.counts == counts:
            prior.validations += 1
        else:
            self._record = _Record(key, counts, 1)
        return self._record.validations

    def reset(self) -> None:
        self._record = None

    def satisfied(self, key: str) -> bool:
        return self.validations(key) >= self.required
