"""The governor: a loop that cycles until converged, then hands off once."""

from pathlib import Path

from elegant.authorization import grant
from elegant.tagteam import TagTeam

from fakes import FakeFinisher, FakeProposer, StuckProposer


def _tree(root: Path) -> None:
    (root / "pkg").mkdir()
    (root / "pkg" / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_x.py").write_text(
        "def test_a():\n    assert True\n", encoding="utf-8")
    (root / "NOTE.md").write_text("old note\n", encoding="utf-8")


def _auth(root: Path):
    return grant("william", "transform", str(root.resolve()), "documentation", "test")


def _read(root: Path, name: str) -> str:
    return (root / name).read_text(encoding="utf-8")


def test_missing_auth_does_not_write(tmp_path: Path):
    _tree(tmp_path)
    result = TagTeam(proposer=FakeProposer()).run(tmp_path, findings=[], authorization=None)
    assert result.decision == "REFUSED" and result.applied is False
    assert _read(tmp_path, "NOTE.md") == "old note\n"
    assert result.cycles[0].proposal is not None and result.cycles[0].proposal.edits


def test_no_proposer_means_observe_only(tmp_path: Path):
    _tree(tmp_path)
    result = TagTeam().run(tmp_path, findings=[], authorization=_auth(tmp_path))
    assert result.decision == "INCONCLUSIVE" and not result.applied and result.cycles == ()
    assert _read(tmp_path, "NOTE.md") == "old note\n"


def test_loop_cycles_until_the_proposer_runs_dry(tmp_path: Path):
    _tree(tmp_path)
    proposer = FakeProposer(steps=("one\n", "two\n", "three\n"))
    result = TagTeam(proposer=proposer).run(tmp_path, findings=[], authorization=_auth(tmp_path))
    assert result.converged and result.decision == "ACCEPT"
    assert [c.outcome for c in result.cycles] == ["APPLIED"] * 3 + ["NOTHING_TO_PROPOSE"]
    assert _read(tmp_path, "NOTE.md") == "three\n"


def test_finisher_runs_once_and_only_after_the_loop(tmp_path: Path):
    _tree(tmp_path)
    finisher = FakeFinisher()
    result = TagTeam(proposer=FakeProposer(steps=("a\n", "b\n")), finisher=finisher).run(
        tmp_path, findings=[], authorization=_auth(tmp_path))
    assert finisher.calls == 1 and result.finished and result.decision == "ACCEPT"
    assert _read(tmp_path, "README.md") == "final\n" and _read(tmp_path, "NOTE.md") == "b\n"


def test_finisher_is_not_called_when_the_loop_does_not_converge(tmp_path: Path):
    _tree(tmp_path)
    finisher = FakeFinisher()
    result = TagTeam(proposer=StuckProposer(), finisher=finisher, max_cycles=3).run(
        tmp_path, findings=[], authorization=_auth(tmp_path))
    assert result.decision == "NOT_CONVERGED" and finisher.calls == 0 and not result.finished


def test_max_cycles_stops_a_proposer_that_never_runs_dry(tmp_path: Path):
    _tree(tmp_path)
    proposer = FakeProposer(steps=[f"v{i}\n" for i in range(9)])
    result = TagTeam(proposer=proposer, max_cycles=2).run(
        tmp_path, findings=[], authorization=_auth(tmp_path))
    assert result.decision == "NOT_CONVERGED" and len(result.cycles) == 2


def test_a_cycle_that_breaks_the_suite_is_put_back_and_stops_the_loop(tmp_path: Path):
    _tree(tmp_path)
    breaking = "def test_a():\n    assert False\n"
    proposer = FakeProposer(steps=(breaking,), path="tests/test_x.py")
    result = TagTeam(proposer=proposer).run(tmp_path, findings=[], authorization=_auth(tmp_path))
    assert result.decision == "REJECT" and result.cycles[-1].outcome == "PUT_BACK"
    assert _read(tmp_path, "tests/test_x.py") == "def test_a():\n    assert True\n"


def test_a_finisher_that_breaks_the_suite_is_put_back_but_the_loop_result_stands(tmp_path: Path):
    _tree(tmp_path)
    breaking = FakeFinisher(path="tests/test_x.py", new_text="def test_a():\n    assert False\n")
    result = TagTeam(proposer=FakeProposer(steps=("kept\n",)), finisher=breaking).run(
        tmp_path, findings=[], authorization=_auth(tmp_path))
    assert result.decision == "FINISH_REJECTED" and result.converged and not result.finished
    assert _read(tmp_path, "tests/test_x.py") == "def test_a():\n    assert True\n"
    assert _read(tmp_path, "NOTE.md") == "kept\n"


def test_the_finisher_is_handed_the_measured_facts(tmp_path: Path):
    _tree(tmp_path)
    finisher = FakeFinisher()
    findings = [{"id": "ghost-1", "severity": "minor", "status": "confirmed", "summary": "left over"}]
    TagTeam(proposer=FakeProposer(steps=()), finisher=finisher).run(
        tmp_path, findings=findings, authorization=_auth(tmp_path))
    assert finisher.facts.suite.green and finisher.facts.suite.passed == 1
    assert [d.ghost_id for d in finisher.facts.remaining] == ["ghost-1"]
    assert finisher.facts.cycles == 0
