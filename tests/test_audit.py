"""Rule 9: defect IDs never change meaning, and the author's text survives."""
import json
from pathlib import Path

from warden import audit
from warden.cli import main


def _f(gid, sev="major", det="dead_code", summary="x"):
    return {"id": gid, "severity": sev, "detector": det, "summary": summary,
            "evidence": {"file": "pkg/m.py", "line_start": 3}}


def test_ids_survive_reruns_and_are_never_reused():
    first = audit.update("", [_f("ghost-a"), _f("ghost-b", "minor")])
    assert "| H1 |" in first and "| M1 |" in first
    # ghost-a disappears, a new major finding arrives: it is H2, not H1.
    second = audit.update(first, [_f("ghost-b", "minor"), _f("ghost-c")])
    rows = {r.ghost: r for r in audit.existing_rows(second)}
    assert rows["ghost-a"].id == "H1" and rows["ghost-a"].status == "not seen in latest scan"
    assert rows["ghost-c"].id == "H2"
    assert rows["ghost-b"].id == "M1"


def test_a_fixed_defect_that_comes_back_is_reopened_under_its_own_id():
    text = audit.update("", [_f("ghost-a")])
    text = text.replace("| H1 | HIGH | Open |", "| H1 | HIGH | Fixed abc1234 |")
    again = audit.update(text, [_f("ghost-a")])
    row = audit.existing_rows(again)[0]
    assert row.id == "H1" and row.status == "Reopened (was Fixed abc1234)"


def test_the_authors_sections_are_kept_byte_for_byte():
    text = audit.update("", [_f("ghost-a")])
    text = text.replace("## Layer map\n\nUNKNOWN: written by a person, not generated.",
                        "## Layer map\n\nAdmission -> Decision -> Custody.")
    again = audit.update(text, [_f("ghost-b")])
    assert "Admission -> Decision -> Custody." in again


def test_cli_prints_without_a_grant_and_writes_with_one(tmp_path: Path, capsys):
    findings = tmp_path / "f.json"
    findings.write_text(json.dumps([_f("ghost-a", "critical")]), encoding="utf-8")
    assert main(["audit", str(tmp_path), "--from-ghost", str(findings)]) == 0
    assert "| C1 |" in capsys.readouterr().out
    assert not (tmp_path / audit.FILENAME).exists()
    assert main(["audit", str(tmp_path), "--from-ghost", str(findings),
                 "--authorize", "william", "--reason", "first audit"]) == 0
    assert "| C1 |" in (tmp_path / audit.FILENAME).read_text(encoding="utf-8")


def test_cli_refuses_self_authorization_and_an_audit_of_nothing(tmp_path: Path):
    findings = tmp_path / "f.json"
    findings.write_text("[]", encoding="utf-8")
    assert main(["audit", str(tmp_path), "--from-ghost", str(findings),
                 "--authorize", "warden", "--reason", "x"]) == 2
    assert main(["audit", str(tmp_path)]) == 2


def test_audit_runs_as_a_module_command(tmp_path: Path):
    """`python -m warden.cli audit` once failed with NameError: the helper sat
    below the __main__ guard, so importing tests passed and the command broke."""
    import subprocess
    import sys
    findings = tmp_path / "f.json"
    findings.write_text(json.dumps([_f("ghost-a")]), encoding="utf-8")
    done = subprocess.run([sys.executable, "-m", "warden.cli", "audit", str(tmp_path),
                           "--from-ghost", str(findings)], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert "| H1 |" in done.stdout
