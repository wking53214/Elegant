"""CNS analysis never writes, and CNS itself is NO_ACTION."""

from pathlib import Path

from elegant.cns_boundary import CnsRecommendation, analyse


def test_unrelated_repo_is_no_action(tmp_path: Path):
    (tmp_path / "x.py").write_text("print('hi')\n", encoding="utf-8")
    a = analyse(tmp_path)
    assert a.recommendation is CnsRecommendation.NO_ACTION
    assert a.cns_modified == "NO"
    # did not write anything extra
    assert list(p.name for p in tmp_path.iterdir()) == ["x.py"]


def test_cns_named_tree_is_never_a_rewrite_target(tmp_path: Path):
    cns = tmp_path / "CNS"
    cns.mkdir()
    (cns / "cns").mkdir()
    (cns / "cns" / "__init__.py").write_text('"""cns contracts."""\n', encoding="utf-8")
    a = analyse(cns)
    assert a.recommendation is CnsRecommendation.NO_ACTION
    assert "does not modify" in a.reason.lower() or "DEFER" in a.reason
    assert a.cns_modified == "NO"
