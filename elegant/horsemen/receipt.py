"""Production receipt for horsemen-mediated transformations."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

@dataclass
class ProductionReceipt:
    receipt_id: str
    repository: str
    before_revision: str
    after_revision: str
    baseline_id: str
    transformation_id: str
    proposal_id: str
    authorization_id: str
    actor: str
    authority_source: str
    change_class: str
    scope_summary: str
    findings_addressed: List[str] = field(default_factory=list)
    findings_remaining: List[str] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)
    specimens_used: List[str] = field(default_factory=list)
    adversarial_cases: List[str] = field(default_factory=list)
    regression_results: Dict[str, str] = field(default_factory=dict)
    files_changed: List[str] = field(default_factory=list)
    invariants_checked: List[str] = field(default_factory=list)
    cns_readiness: str = "UNKNOWN"
    cns_adapter_location: Optional[str] = None
    bypass_tests: Dict[str, str] = field(default_factory=dict)
    final_verdict: str = "UNKNOWN"
    handoff_ids: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    schema_version: str = "1.0.0"

    def __post_init__(self):
        if self.cns_readiness == "UNKNOWN" and self.final_verdict == "CNS_READY":
            raise ValueError("FORBIDDEN: UNKNOWN cns_readiness cannot yield CNS_READY")

    def to_dict(self):
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

def emit_receipt(**kwargs):
    return ProductionReceipt(receipt_id=f"prcp_{uuid.uuid4().hex[:12]}", **kwargs)
