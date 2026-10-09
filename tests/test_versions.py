"""`versions` reads commits and version strings from files, and says None when it cannot."""

import subprocess

from warden import versions


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                   env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                        "GIT_COMMITTER_EMAIL": "t@t", "PATH": "/usr/bin:/bin", "HOME": str(cwd)})


def _repo(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "1.2.3"\n', encoding="utf-8")
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "one")
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True,
                          check=True).stdout.strip()


def test_the_commit_and_version_of_a_checkout_are_read_without_running_git(tmp_path):
    sha = _repo(tmp_path)
    got = versions.instrument(tmp_path)
    assert got == {"path": str(tmp_path.resolve()), "commit": sha, "version": "1.2.3"}


def test_a_commit_is_found_from_packed_refs_and_from_a_subfolder(tmp_path):
    sha = _repo(tmp_path)
    _git(tmp_path, "pack-refs", "--all")
    (tmp_path / "sub").mkdir()
    assert versions.git_commit(tmp_path / "sub") == sha


def test_a_detached_head_is_read(tmp_path):
    sha = _repo(tmp_path)
    _git(tmp_path, "checkout", "-q", "--detach")
    assert versions.git_commit(tmp_path) == sha


def test_a_folder_that_is_not_a_checkout_reports_none_not_a_guess(tmp_path):
    got = versions.instrument(tmp_path)
    assert got["commit"] is None and got["version"] is None


def test_nothing_given_is_none():
    assert versions.instrument(None) is None
    assert versions.seat(None, object()) is None


def test_a_broken_pyproject_is_none(tmp_path):
    (tmp_path / "pyproject.toml").write_text("not [ toml", encoding="utf-8")
    assert versions.project_version(tmp_path) is None
