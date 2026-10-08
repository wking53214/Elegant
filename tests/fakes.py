"""Stand-ins for the two seats, with no opinion about code at all.

The real ones are Proposer and Streamline. Elegant's tests must not depend on
them (Elegant never imports either), so the governor is exercised with these:
they propose whatever edits the test hands them.
"""

from __future__ import annotations

from pathlib import Path

from elegant.models import FileEdit, Transformation, TransformationStatus


def _transformation(target, observed, baseline, path, new_text) -> Transformation:
    target = Path(target)
    note = target / path
    old = note.read_text(encoding="utf-8") if note.is_file() else ""
    return Transformation(
        target=str(target.resolve()), intent="test change", architectural_reason="test",
        affected_files=(path,), expected_behavior="none", preservation_requirements=(),
        known_defects=observed, transformation_scope="documentation",
        baseline_reference=baseline, evidence=(),
        edits=(FileEdit(path=path, kind="write", new=new_text, old=old),),
        status=TransformationStatus.PROPOSED)


class FakeProposer:
    """Proposes the next text in `steps` (one per call), then runs dry."""

    def __init__(self, steps=("changed\n",), path="NOTE.md"):
        self.steps, self.path, self.calls = list(steps), path, 0

    def propose(self, target, observed, baseline):
        self.calls += 1
        if not self.steps:
            return None
        return _transformation(target, observed, baseline, self.path, self.steps.pop(0))


class StuckProposer:
    """Proposes the same thing forever; the loop must notice."""

    def __init__(self, path="NOTE.md"):
        self.path, self.n = path, 0

    def propose(self, target, observed, baseline):
        self.n += 1
        return _transformation(target, observed, baseline, self.path, f"v{self.n % 2}\n")


class FakeFinisher:
    def __init__(self, path="README.md", new_text="final\n"):
        self.path, self.new_text, self.calls = path, new_text, 0

    def finish(self, target, baseline):
        self.calls += 1
        return _transformation(target, (), baseline, self.path, self.new_text)
