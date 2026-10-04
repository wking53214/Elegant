"""The critic may not praise a lying README."""

from pathlib import Path

from elegant.critic import PoetryCritic
from elegant.narrative import inspect_tree


def _pkg(root: Path, readme: str, tests: int = 2) -> None:
    (root / "pkg").mkdir()
    (root / "pkg" / "__init__.py").write_text('"""owns nothing declared."""\n', encoding="utf-8")
    tdir = root / "tests"
    tdir.mkdir()
    body = "\n".join(f"def test_{i}():\n    assert True\n" for i in range(tests))
    (tdir / "test_x.py").write_text(body, encoding="utf-8")
    (root / "README.md").write_text(readme, encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.0.1"\ndescription = "demo"\n',
        encoding="utf-8",
    )


def test_false_test_count_is_not_good_enough(tmp_path: Path):
    _pkg(tmp_path, "# demo\n\nAll 16 tests passed unmodified on python3.\n")
    report = PoetryCritic().critique(tmp_path)
    assert report.good_enough is False
    assert "isn't good enough yet" in report.verdict
    assert report.unsupported


def test_matching_count_is_consistent_not_a_proof(tmp_path: Path):
    _pkg(tmp_path, "# demo\n\n## What It Does NOT Own\n\nNothing.\n\n## Brutally Honest\n\nHonest.\n\nAll 2 tests passed unmodified.\n", tests=2)
    nar = inspect_tree(tmp_path)
    assert nar.test_functions == 2
    report = PoetryCritic().critique(tmp_path, nar)
    assert report.good_enough is True
    assert "not a proof" in report.verdict.lower() or "consistent" in report.verdict.lower()
