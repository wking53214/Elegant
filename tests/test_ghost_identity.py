"""Ghost identity is consumed, not re-hashed."""

from elegant.models import defects_from_ghost


def test_preserves_ghost_id():
    findings = [
        {
            "id": "ghost-deadbeefcafe",
            "detector": "doc_test_count_drift",
            "category": "doc_drift",
            "severity": "minor",
            "status": "confirmed",
            "summary": "claims 16 tests",
            "detail": "",
            "evidence": {"file": "PROVENANCE.md", "line_start": 76},
        }
    ]
    d = defects_from_ghost(findings)[0]
    assert d.ghost_id == "ghost-deadbeefcafe"
    assert d.human_id == "M1"
    assert d.ghost_status == "confirmed"
    assert d.identity == "ghost-deadbeefcafe"


def test_major_maps_to_high_not_critical():
    findings = [
        {
            "id": "ghost-aaa",
            "detector": "long_function",
            "severity": "major",
            "status": "confirmed",
            "summary": "too long",
            "evidence": {"file": "a.py"},
        }
    ]
    d = defects_from_ghost(findings)[0]
    assert d.severity.value == "high"
    assert d.human_id == "H1"
