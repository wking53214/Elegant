"""TOUCHSTONE -> Elegant: the answer key arrives, or the run says why it did not.

The original adapter returned [] when the registry file was missing, which is
indistinguishable from "TOUCHSTONE has no specimens". These tests pin the
loud behaviour, and the last one reads the real TOUCHSTONE checkout when
TOUCHSTONE_ROOT points at one.
"""
import json
import os
from pathlib import Path

import pytest

from elegant.horsemen import HorsemenWorkflow, TouchstoneAdapter, TouchstoneUnavailable
from elegant.horsemen.authorization_scope import ChangeClass


def _corpus(root: Path, entries: dict) -> Path:
    (root / "touchstone_production").mkdir(parents=True)
    (root / "specimens").mkdir()
    (root / "specimens" / "a.py").write_text("x = 1\n", encoding="utf-8")
    reg = root / "touchstone_production" / "registry.json"
    reg.write_text(json.dumps(entries), encoding="utf-8")
    return reg


GOOD = {"a": {"specimen_id": "a", "specimen_class": "REFERENCE", "path": "specimens/a.py",
              "expected_verdict": "ACCEPT", "epistemic_status": "RECORDED_IN_MANIFEST"}}


def test_no_root_is_an_error_not_an_empty_list():
    with pytest.raises(TouchstoneUnavailable):
        TouchstoneAdapter().load_registry()


def test_missing_registry_is_an_error(tmp_path: Path):
    with pytest.raises(TouchstoneUnavailable, match="not found"):
        TouchstoneAdapter(tmp_path).load_registry()


def test_empty_registry_is_an_error(tmp_path: Path):
    _corpus(tmp_path, {})
    with pytest.raises(TouchstoneUnavailable, match="empty"):
        TouchstoneAdapter(tmp_path).load_registry()


def test_registry_naming_a_missing_file_is_an_error(tmp_path: Path):
    _corpus(tmp_path, {"b": dict(GOOD["a"], specimen_id="b", path="specimens/nope.py")})
    with pytest.raises(TouchstoneUnavailable, match="do not exist"):
        TouchstoneAdapter(tmp_path).load_registry()


def test_good_registry_loads_and_hands_off(tmp_path: Path):
    _corpus(tmp_path, GOOD)
    specs = TouchstoneAdapter(tmp_path).load_registry()
    assert [s.expected_verdict for s in specs] == ["ACCEPT"]
    wf = HorsemenWorkflow(touchstone=TouchstoneAdapter(tmp_path))
    st = wf.start(repository="demo", baseline_id="b0", baseline_sha="0" * 40,
                  change_class=ChangeClass.DOCUMENTATION_ONLY)
    hof = wf.ingest_specimens(st.workflow_id, specs)
    assert hof.result == "SPECIMENS_PROVIDED"
    assert st.phases[-1].result == "SPECIMENS_PROVIDED"


def test_empty_specimen_handoff_is_unknown_not_ok(tmp_path: Path):
    wf = HorsemenWorkflow(touchstone=TouchstoneAdapter(tmp_path))
    st = wf.start(repository="demo", baseline_id="b0", baseline_sha="0" * 40,
                  change_class=ChangeClass.DOCUMENTATION_ONLY)
    hof = wf.ingest_specimens(st.workflow_id, [])
    assert hof.result == "NO_SPECIMENS_UNKNOWN"
    assert st.phases[-1].result != "ok"


@pytest.mark.skipif(not os.environ.get("TOUCHSTONE_ROOT"),
                    reason="set TOUCHSTONE_ROOT to a TOUCHSTONE checkout to run the live link")
def test_live_touchstone_registry():
    specs = TouchstoneAdapter(os.environ["TOUCHSTONE_ROOT"]).load_registry()
    by_id = {s.specimen_id: s for s in specs}
    # MANIFEST.md section 3.1: the silent pass must be refused.
    assert by_id["fm_3_1_silent_pass"].expected_verdict == "REFUSE"
    classes = {s.specimen_class for s in specs}
    assert {"RECONSTRUCTION_PAIR", "FAILURE_MODE", "REFERENCE", "SUPERSEDED"} <= classes
