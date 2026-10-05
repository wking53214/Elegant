"""Four Horsemen interface for Elegant."""
from .contracts import Handoff, HandoffKind, EpistemicLabel, try_import_shared_contracts
from .authorization_scope import (
    ScopedGrant, ScopeSpec, ChangeClass, grant_scoped, validate_scoped, ScopeViolation,
)
from .adapters import (
    TouchstoneAdapter, GhostToolsAdapter, SwizzleAdapter,
    SpecimenRef, GhostFinding, SwizzleVerdict,
)
from .workflow import HorsemenWorkflow, WorkflowPhase, WorkflowState
from .receipt import ProductionReceipt, emit_receipt

__all__ = [
    "Handoff", "HandoffKind", "EpistemicLabel", "try_import_shared_contracts",
    "ScopedGrant", "ScopeSpec", "ChangeClass", "grant_scoped", "validate_scoped", "ScopeViolation",
    "TouchstoneAdapter", "GhostToolsAdapter", "SwizzleAdapter",
    "SpecimenRef", "GhostFinding", "SwizzleVerdict",
    "HorsemenWorkflow", "WorkflowPhase", "WorkflowState",
    "ProductionReceipt", "emit_receipt",
]
