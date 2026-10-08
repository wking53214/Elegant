"""A craft for testing the governor, with no opinion about code at all.

The real craft is Streamline. Elegant's tests must not depend on it (Elegant
never imports Streamline), so the governor is exercised with this stand-in:
it proposes whatever edits the test hands it and answers review and attack
with whatever the test says.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from elegant.craft import AttackResult, Review
from elegant.models import FileEdit, Transformation, TransformationStatus


@dataclass(frozen=True)
class Frozen:
    fingerprint: str


class FakeCraft:
    """Writes `new_text` to `path`; reports the verdicts it was built with."""

    def __init__(self, path="NOTE.md", new_text="changed\n", *, good_after=True, attack="ACCEPT"):
        self.path, self.new_text = path, new_text
        self.good_after, self.attack_judgement = good_after, attack
        self._reviews = 0

    def freeze(self, target: Path) -> Frozen:
        note = Path(target) / self.path
        blob = note.read_bytes() if note.is_file() else b""
        return Frozen(hashlib.sha256(blob).hexdigest()[:16])

    def review(self, target: Path) -> Review:
        self._reviews += 1
        good = self.good_after or self._reviews == 1
        return Review(good_enough=good, verdict="fine" if good else "This isn't good enough yet.")

    def propose(self, target, observed, ground) -> Transformation:
        target = Path(target)
        note = target / self.path
        old = note.read_text(encoding="utf-8") if note.is_file() else ""
        return Transformation(
            target=str(target.resolve()), intent="test change", architectural_reason="test",
            affected_files=(self.path,), expected_behavior="none", preservation_requirements=(),
            known_defects=observed, transformation_scope="documentation",
            baseline_reference=ground.fingerprint, evidence=(),
            edits=(FileEdit(path=self.path, kind="write", new=self.new_text, old=old),),
            status=TransformationStatus.PROPOSED)

    def attack(self, target: Path, ground) -> AttackResult:
        return AttackResult(self.attack_judgement, (), "fake attack")
