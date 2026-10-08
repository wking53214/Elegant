"""Authorization is a refusal by default. Warden cannot grant itself."""

from pathlib import Path

import pytest

from warden.authorization import Unauthorized, grant, refuse
from warden.models import FileEdit, Transformation, TransformationStatus


def test_refuse_is_not_a_grant():
    a = refuse("human", "transform", "/tmp/x", "not yet")
    assert a.granted is False
    assert a.permits("transform", "/tmp/x") is False


def test_warden_cannot_authorize_itself():
    with pytest.raises(Unauthorized):
        grant("warden", "transform", "/tmp/x", "docs", "because")
    with pytest.raises(Unauthorized):
        grant("self", "transform", "/tmp/x", "docs", "because")
    with pytest.raises(Unauthorized):
        grant("unknown", "transform", "/tmp/x", "docs", "because")


def test_grant_requires_a_reason():
    with pytest.raises(Unauthorized):
        grant("william", "transform", "/tmp/x", "docs", "   ")


def test_apply_without_authorization_raises(tmp_path: Path):
    p = tmp_path / "README.md"
    p.write_text("hello\n", encoding="utf-8")
    t = Transformation(
        target=str(tmp_path),
        intent="rewrite",
        architectural_reason="test",
        affected_files=("README.md",),
        expected_behavior="text changes",
        preservation_requirements=(),
        known_defects=(),
        transformation_scope="docs",
        baseline_reference="x",
        evidence=(),
        edits=(FileEdit(path="README.md", kind="write", new="goodbye\n"),),
    )
    with pytest.raises(Unauthorized):
        t.apply(tmp_path)
    assert p.read_text(encoding="utf-8") == "hello\n"


def test_apply_with_grant_writes(tmp_path: Path):
    p = tmp_path / "README.md"
    p.write_text("hello\n", encoding="utf-8")
    t = Transformation(
        target=str(tmp_path),
        intent="rewrite",
        architectural_reason="test",
        affected_files=("README.md",),
        expected_behavior="text changes",
        preservation_requirements=(),
        known_defects=(),
        transformation_scope="docs",
        baseline_reference="x",
        evidence=(),
        edits=(FileEdit(path="README.md", kind="write", new="goodbye\n"),),
        status=TransformationStatus.PROPOSED,
    )
    auth = grant("william", "transform", str(tmp_path), "docs", "fixture")
    t.authorize(auth)
    result = t.apply(tmp_path)
    assert result["written"] == ["README.md"]
    assert p.read_text(encoding="utf-8") == "goodbye\n"
