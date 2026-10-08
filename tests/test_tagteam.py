"""The governor: observe, propose, authorize, gate on the suite, attack, decide."""

from pathlib import Path

from elegant.authorization import grant
from elegant.tagteam import TagTeam

from fakes import FakeCraft


def _tree(root: Path) -> None:
    (root / "pkg").mkdir()
    (root / "pkg" / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_x.py").write_text(
        "def test_a():\n    assert True\n", encoding="utf-8")
    (root / "NOTE.md").write_text("old note\n", encoding="utf-8")


def _auth(root: Path):
    return grant("william", "transform", str(root.resolve()), "documentation", "test")


def test_missing_auth_does_not_write(tmp_path: Path):
    _tree(tmp_path)
    result = TagTeam(craft=FakeCraft()).run(tmp_path, findings=[], authorization=None)
    assert result.decision == "REFUSED" and result.applied is False
    assert (tmp_path / "NOTE.md").read_text(encoding="utf-8") == "old note\n"
    assert result.proposal is not None and result.proposal.edits


def test_authorized_change_is_applied_and_accepted(tmp_path: Path):
    _tree(tmp_path)
    result = TagTeam(craft=FakeCraft()).run(tmp_path, findings=[], authorization=_auth(tmp_path))
    assert result.applied and result.decision == "ACCEPT"
    assert (tmp_path / "NOTE.md").read_text(encoding="utf-8") == "changed\n"
    assert result.review_before.good_enough and result.review_after.good_enough


def test_a_failed_attack_outvotes_a_good_review(tmp_path: Path):
    _tree(tmp_path)
    result = TagTeam(craft=FakeCraft(attack="REJECT")).run(
        tmp_path, findings=[], authorization=_auth(tmp_path))
    assert result.decision == "REJECT"


def test_a_good_attack_does_not_outvote_a_bad_review(tmp_path: Path):
    _tree(tmp_path)
    result = TagTeam(craft=FakeCraft(good_after=False)).run(
        tmp_path, findings=[], authorization=_auth(tmp_path))
    assert result.decision == "REJECT"
    assert any("not good enough yet" in n for n in result.notes)


def test_no_craft_means_observe_only(tmp_path: Path):
    _tree(tmp_path)
    result = TagTeam().run(tmp_path, findings=[], authorization=_auth(tmp_path))
    assert result.decision == "INCONCLUSIVE" and not result.applied
    assert result.review_before is None and result.baseline == "UNKNOWN"
    assert (tmp_path / "NOTE.md").read_text(encoding="utf-8") == "old note\n"


def _fake_swizzle(root: Path, exit_code: int, summary: str) -> Path:
    pkg = root / "fake_swizzle" / "swizzle"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "cli.py").write_text(
        f"import sys\nprint({summary!r})\nsys.exit({exit_code})\n", encoding="utf-8")
    return root / "fake_swizzle"


def test_swizzle_proofs_failing_blocks_accept(tmp_path: Path):
    target = tmp_path / "repo"
    target.mkdir()
    _tree(target)
    bad = _fake_swizzle(tmp_path, 1, "11 of 12 proofs hold.")
    result = TagTeam(swizzle_root=bad, craft=FakeCraft()).run(
        target, authorization=_auth(target), findings=[])
    assert result.decision == "INCONCLUSIVE"
    assert result.swizzle_sound is False and not result.applied
    assert (target / "NOTE.md").read_text(encoding="utf-8") == "old note\n"
    assert any("11 of 12 proofs hold" in n for n in result.notes)


def test_swizzle_not_configured_is_said_out_loud(tmp_path: Path):
    target = tmp_path / "repo"
    target.mkdir()
    _tree(target)
    result = TagTeam().run(target, findings=[])
    assert any("SWIZZLE proofs NOT RUN" in n for n in result.notes)
