"""Stand-ins for the two seats, with no opinion about code at all.

The real ones are Drafter and Burnish. Warden's tests must not depend on
them (Warden never imports either), so the governor is exercised with these:
they propose whatever edits the test hands them.
"""

from __future__ import annotations

from pathlib import Path

from warden.models import FileEdit, Transformation, TransformationStatus


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


class FakeDrafter:
    """Proposes the next text in `steps` (one per call), then runs dry."""

    def __init__(self, steps=("changed\n",), path="NOTE.md"):
        self.steps, self.path, self.calls = list(steps), path, 0

    def propose(self, target, observed, baseline):
        self.calls += 1
        if not self.steps:
            return None
        return _transformation(target, observed, baseline, self.path, self.steps.pop(0))


class StuckDrafter:
    """Proposes the same thing forever; the loop must notice."""

    def __init__(self, path="NOTE.md"):
        self.path, self.n = path, 0

    def propose(self, target, observed, baseline):
        self.n += 1
        return _transformation(target, observed, baseline, self.path, f"v{self.n % 2}\n")


class FakeFinisher:
    def __init__(self, path="README.md", new_text="final\n"):
        self.path, self.new_text, self.calls, self.facts = path, new_text, 0, None

    def finish(self, target, baseline, facts):
        self.calls += 1
        self.facts = facts
        return _transformation(target, (), baseline, self.path, self.new_text)


class RemovingDrafter:
    """Proposes deleting `path`, citing a Ghost finding, every time it is asked."""

    def __init__(self, path="pkg/dead.py", cites="ghost-dead1"):
        self.path, self.cites, self.calls = path, cites, 0

    def propose(self, target, observed, baseline):
        from warden.models import Defect, DefectSeverity
        target = Path(target)
        path = target / self.path
        if not path.is_file() or "WARDEN COMMENTED OUT" in path.read_text(encoding="utf-8"):
            return None
        self.calls += 1
        defect = Defect(summary="unused", severity=DefectSeverity.LOW, ghost_id=self.cites)
        return Transformation(
            target=str(target.resolve()), intent="remove unused code", architectural_reason="test",
            affected_files=(self.path,), expected_behavior="none", preservation_requirements=(),
            known_defects=(defect,), transformation_scope="code", baseline_reference=baseline,
            evidence=(), edits=(FileEdit(path=self.path, kind="delete", new=""),),
            status=TransformationStatus.PROPOSED)
