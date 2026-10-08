"""Final integration registry.

Machine-readable record of what this campaign actually did. UNKNOWN is a
valid cell. Do not invent passing tests or remote SHAs.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class RegistryRow:
    repository: str
    baseline_sha: str
    final_sha: str = "UNKNOWN"
    branch: str = "UNKNOWN"
    warden_involvement: str = "none"
    ghost_tools_involvement: str = "none"
    swizzle_involvement: str = "none"
    readme_rewritten: bool = False
    cns_involvement: str = "none"
    cns_integration_type: str = "none"
    internal_convergence: bool = False
    adapter: bool = False
    authoritative_path: str = "UNKNOWN"
    cns_seam: str = "none"
    native_representation: str = "UNKNOWN"
    cns_representation: str = "none"
    subject_binding: str = "UNKNOWN"
    authority_model: str = "UNKNOWN"
    epistemic_model: str = "UNKNOWN"
    provenance_model: str = "UNKNOWN"
    digest_model: str = "UNKNOWN"
    tests_executed: str = "UNKNOWN"
    adversarial_validation_executed: str = "UNKNOWN"
    known_defects: str = "UNKNOWN"
    architectural_debt: str = "UNKNOWN"
    unknown: str = ""
    push_status: str = "UNKNOWN"
    remote_verification: str = "UNKNOWN"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_registry(path: Path, rows: list[RegistryRow]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "cns_modified": "NO",
        "rows": [r.to_dict() for r in rows],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_registry(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
