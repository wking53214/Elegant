"""Tag team: observe → propose → authorize → apply → independent attack."""

from pathlib import Path

from elegant.authorization import grant
from elegant.proposers import documentation_honesty_proposer
from elegant.tagteam import TagTeam


def _tree(root: Path) -> None:
    (root / "pkg").mkdir()
    (root / "pkg" / "__init__.py").write_text('"""demo package."""\n', encoding="utf-8")
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_x.py").write_text(
        "def test_a():\n    assert True\n\ndef test_b():\n    assert True\n",
        encoding="utf-8",
    )
    (root / "PROVENANCE.md").write_text(
        "All 16 tests passed unmodified on the system python3.\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text("# demo\n\nSee provenance.\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.0.1"\ndescription = "demo"\n',
        encoding="utf-8",
    )


def test_missing_auth_does_not_write(tmp_path: Path):
    _tree(tmp_path)
    team = TagTeam(proposer=documentation_honesty_proposer)
    findings = [
        {
            "id": "ghost-abc",
            "detector": "doc_test_count_drift",
            "severity": "minor",
            "status": "confirmed",
            "summary": "PROVENANCE.md claims 16 test(s)",
            "evidence": {"file": "PROVENANCE.md"},
        }
    ]
    result = team.run(tmp_path, findings=findings, authorization=None)
    assert result.decision == "REFUSED"
    assert result.applied is False
    assert "All 16 tests passed" in (tmp_path / "PROVENANCE.md").read_text(encoding="utf-8")
    assert result.proposal is not None
    assert result.proposal.edits


def test_authorized_rewrite_survives_honesty_oracle(tmp_path: Path):
    _tree(tmp_path)
    team = TagTeam(proposer=documentation_honesty_proposer)
    findings = [
        {
            "id": "ghost-abc",
            "detector": "doc_test_count_drift",
            "severity": "minor",
            "status": "confirmed",
            "summary": "PROVENANCE.md claims 16 test(s)",
            "evidence": {"file": "PROVENANCE.md"},
        }
    ]
    auth = grant("william", "transform", str(tmp_path.resolve()), "documentation", "vertical slice fixture")
    result = team.run(tmp_path, findings=findings, authorization=auth)
    text = (tmp_path / "PROVENANCE.md").read_text(encoding="utf-8")
    assert "16" in text  # historical number preserved
    assert "All 16 tests passed unmodified" not in text
    assert result.applied is True
    assert result.attack is not None
    assert result.attack.judgement == "ACCEPT"
    assert result.decision in {"ACCEPT", "REJECT"}  # critic may still find other ugliness
    # python sources untouched
    assert '"""demo package."""' in (tmp_path / "pkg" / "__init__.py").read_text(encoding="utf-8")
