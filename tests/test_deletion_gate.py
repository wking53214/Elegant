"""Code is removed only after two loop validations; anything else is refused."""

from pathlib import Path

import pytest

import warden.tagteam as tagteam
from warden.authorization import grant
from warden.deletion import DeletionGate, is_deletion
from warden.models import FileEdit
from warden.tagteam import TagTeam

from fakes import FakeDrafter, RemovingDrafter

DEAD = {"id": "ghost-dead1", "severity": "minor", "summary": "unused", "status": "confirmed"}


def _repo(root: Path) -> None:
    (root / "pkg").mkdir()
    (root / "pkg" / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "pkg" / "dead.py").write_text("def unused():\n    return 1\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_pkg.py").write_text(
        "from pkg import VALUE\n\ndef test_value():\n    assert VALUE == 1\n", encoding="utf-8")
    (root / "pyproject.toml").write_text('[project]\nname = "demo"\nversion = "0.0.1"\n',
                                          encoding="utf-8")


def _auth(root: Path):
    return grant("william", "transform", str(root.resolve()), "code", "deletion test")


@pytest.fixture
def ghost(monkeypatch):
    """Ghost reports the dead-code finding while the file exists."""
    state = {"scans": 0, "report": True}

    def fake_scan(target, **kw):
        state["scans"] += 1
        exists = (Path(target) / "pkg" / "dead.py").is_file()
        return (DEAD,) if state["report"] and exists else ()

    monkeypatch.setattr(tagteam, "ghost_scan", fake_scan)
    monkeypatch.setattr(TagTeam, "_calibrate", lambda self, python, notes: True)
    return state


def _team(**kw):
    return TagTeam(drafter=RemovingDrafter(), ghost_tools_root=Path("."), **kw)


def test_a_removal_waits_for_two_validations_then_applies(tmp_path, ghost):
    _repo(tmp_path)
    result = _team().run(tmp_path, findings=[DEAD], authorization=_auth(tmp_path))
    outcomes = [c.outcome for c in result.cycles]
    assert outcomes == ["HELD", "APPLIED", "NOTHING_TO_PROPOSE"]
    assert not (tmp_path / "pkg" / "dead.py").exists()
    assert result.decision == "ACCEPT"
    assert any("validation 1 of 2" in n for n in result.notes)
    assert any("validation 2 of 2" in n for n in result.notes)


def test_nothing_is_deleted_after_only_one_validation(tmp_path, ghost):
    _repo(tmp_path)
    result = _team(max_cycles=1).run(tmp_path, findings=[DEAD], authorization=_auth(tmp_path))
    assert [c.outcome for c in result.cycles] == ["HELD"]
    assert (tmp_path / "pkg" / "dead.py").exists() and result.decision == "NOT_CONVERGED"


def test_a_finding_that_disappears_between_validations_stops_the_removal(tmp_path, ghost):
    _repo(tmp_path)
    scans = ghost["scans"]

    class Flaky(RemovingDrafter):
        def propose(self, *a):
            if self.calls == 1:
                ghost["report"] = False
            return super().propose(*a)

    result = TagTeam(drafter=Flaky(), ghost_tools_root=Path(".")).run(
        tmp_path, findings=[DEAD], authorization=_auth(tmp_path))
    assert result.decision == "REJECT" and (tmp_path / "pkg" / "dead.py").exists()
    assert any("no longer reports" in n for n in result.notes)


def test_a_removal_without_ghost_is_never_applied(tmp_path, ghost):
    _repo(tmp_path)
    result = TagTeam(drafter=RemovingDrafter()).run(
        tmp_path, findings=[DEAD], authorization=_auth(tmp_path))
    assert result.decision == "REJECT" and (tmp_path / "pkg" / "dead.py").exists()


def test_a_removal_without_the_suite_is_never_applied(tmp_path, ghost):
    _repo(tmp_path)
    result = _team(run_tests=False).run(tmp_path, findings=[DEAD], authorization=_auth(tmp_path))
    assert result.decision == "REJECT" and (tmp_path / "pkg" / "dead.py").exists()


def test_a_removal_is_not_applied_when_swizzle_proofs_fail(tmp_path, ghost, monkeypatch):
    _repo(tmp_path)
    monkeypatch.setattr(TagTeam, "_calibrate", lambda self, python, notes: False)
    result = _team().run(tmp_path, findings=[DEAD], authorization=_auth(tmp_path))
    assert (tmp_path / "pkg" / "dead.py").exists() and not result.applied


def test_a_removal_that_breaks_the_suite_is_put_back_even_after_validation(tmp_path, ghost):
    _repo(tmp_path)
    (tmp_path / "tests" / "test_pkg.py").write_text(
        "from pkg import dead\n\ndef test_dead():\n    assert dead.unused() == 1\n",
        encoding="utf-8")
    result = _team().run(tmp_path, findings=[DEAD], authorization=_auth(tmp_path))
    assert (tmp_path / "pkg" / "dead.py").exists()
    assert result.decision == "REJECT" and any("put back" in n for n in result.notes)


def test_the_applier_refuses_a_removal_that_skipped_the_gate(tmp_path):
    _repo(tmp_path)
    proposal = RemovingDrafter().propose(tmp_path, (), "b")
    done = TagTeam()._apply(tmp_path, proposal, _auth(tmp_path), "python", [], 1, 0)
    assert done.outcome == "REFUSED" and (tmp_path / "pkg" / "dead.py").exists()


def test_the_count_resets_when_the_suite_changes():
    gate = DeletionGate()
    assert gate.record("k", (5, 0, 0)) == 1
    assert gate.record("k", (6, 0, 0)) == 1 and not gate.satisfied("k")
    assert gate.record("k", (6, 0, 0)) == 2 and gate.satisfied("k")
    assert gate.record("other", (6, 0, 0)) == 1


def test_what_counts_as_removing_code(tmp_path):
    _repo(tmp_path)
    t = RemovingDrafter().propose(tmp_path, (), "b")
    assert is_deletion(tmp_path, t)
    shrink = FakeDrafter(steps=("VALUE = 1\n",), path="pkg/dead.py").propose(tmp_path, (), "b")
    assert is_deletion(tmp_path, shrink)
    (tmp_path / "NOTE.md").write_text("a\nb\n", encoding="utf-8")
    prose = FakeDrafter(steps=("a\n",), path="NOTE.md").propose(tmp_path, (), "b")
    assert not is_deletion(tmp_path, prose)
    grow = FakeDrafter(steps=("VALUE = 1\nOTHER = 2\n",), path="pkg/__init__.py").propose(tmp_path, (), "b")
    assert not is_deletion(tmp_path, grow)
