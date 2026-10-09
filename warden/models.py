"""Transformation and defect representations.

A transformation is a *proposal* until an Authorization grants it. Applying
without that grant is a bug in the caller, and this module refuses.

Defect identity: Ghost Tools already owns machine identity (`ghost-<hash>`).
Warden preserves those IDs. Human-readable C1/H1/M1/L1 labels are assigned
only when no Ghost identity exists, and they are labels, not a second authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from .authorization import Authorization, Unauthorized
from .epistemic import EpistemicState


class DefectSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DefectLifecycle(str, Enum):
    IDENTIFIED = "identified"
    PROPOSED = "proposed"
    AUTHORIZED = "authorized"
    MODIFIED = "modified"
    TESTED = "tested"
    ADVERSARIALLY_TESTED = "adversarially_tested"
    FIXED = "fixed"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class InvalidDefectTransition(ValueError):
    """A defect was moved to a state its lifecycle does not allow."""


# Only the moves the code makes today. A state with no entry has no allowed
# next step, so any move out of it is refused.
VALID_DEFECT_TRANSITIONS: dict[DefectLifecycle, frozenset[DefectLifecycle]] = {
    DefectLifecycle.PROPOSED: frozenset(
        {DefectLifecycle.AUTHORIZED, DefectLifecycle.MODIFIED}
    ),
    DefectLifecycle.AUTHORIZED: frozenset({DefectLifecycle.MODIFIED}),
}


def _move_defect(defect: Any, target: DefectLifecycle) -> None:
    allowed = VALID_DEFECT_TRANSITIONS.get(defect.lifecycle, frozenset())
    if target not in allowed:
        raise InvalidDefectTransition(
            f"defect cannot move from {defect.lifecycle.value} "
            f"to {target.value}"
        )
    defect.lifecycle = target


class TransformationStatus(str, Enum):
    DRAFT = "draft"
    PROPOSED = "proposed"
    AUTHORIZED = "authorized"
    APPLIED = "applied"
    REJECTED = "rejected"
    DEFERRED = "deferred"


_SEVERITY_PREFIX = {
    DefectSeverity.CRITICAL: "C",
    DefectSeverity.HIGH: "H",
    DefectSeverity.MEDIUM: "M",
    DefectSeverity.LOW: "L",
}


def human_label(severity: DefectSeverity, index: int) -> str:
    if index < 1:
        raise ValueError("defect index is 1-based")
    return f"{_SEVERITY_PREFIX[severity]}{index}"


def ghost_severity_to_warden(value: str) -> DefectSeverity:
    """Map Ghost Tools severity onto Warden's four-level scale.

    Ghost uses critical/major/minor/informational. Warden uses
    critical/high/medium/low. This is a documented translation, not a claim
    that the two scales are identical.
    """
    v = value.lower()
    if v == "critical":
        return DefectSeverity.CRITICAL
    if v == "major":
        return DefectSeverity.HIGH
    if v == "minor":
        return DefectSeverity.MEDIUM
    if v in {"informational", "info"}:
        return DefectSeverity.LOW
    return DefectSeverity.MEDIUM


@dataclass
class Defect:
    """One architectural or documentary defect.

    `ghost_id` is the authoritative machine identity when present.
    `human_id` is a durable label for prose (C1, H1, …).
    """

    summary: str
    severity: DefectSeverity
    lifecycle: DefectLifecycle = DefectLifecycle.IDENTIFIED
    ghost_id: Optional[str] = None
    human_id: Optional[str] = None
    evidence: tuple[str, ...] = ()
    file: Optional[str] = None
    epistemic: EpistemicState = EpistemicState.UNKNOWN
    ghost_status: Optional[str] = None  # CONFIRMED/REASONED/… preserved verbatim
    #: What Ghost said, verbatim, so a Drafter can act on Ghost's own facts
    #: instead of re-measuring the tree or parsing the summary sentence.
    detector: Optional[str] = None
    line: Optional[int] = None
    attributes: Mapping[str, str] = field(default_factory=dict)

    @property
    def identity(self) -> str:
        return self.ghost_id or self.human_id or self.summary


@dataclass
class Transformation:
    """One intentional change, with a reason, a baseline, and a preservation expectation.

    Warden must not silently alter code. `apply` requires a granted
    Authorization whose operation and subject match this transformation.
    """

    target: str
    intent: str
    architectural_reason: str
    affected_files: tuple[str, ...]
    expected_behavior: str
    preservation_requirements: tuple[str, ...]
    known_defects: tuple[Defect, ...]
    transformation_scope: str
    baseline_reference: str
    evidence: tuple[str, ...]
    edits: tuple["FileEdit", ...] = ()
    status: TransformationStatus = TransformationStatus.PROPOSED
    authorization: Optional[Authorization] = None
    result: Optional[str] = None

    def authorize(self, auth: Authorization) -> "Transformation":
        if not auth.permits("transform", self.target):
            raise Unauthorized(
                f"authorization does not permit transform on {self.target!r} "
                f"(actor={auth.actor!r} granted={auth.granted})"
            )
        self.authorization = auth
        self.status = TransformationStatus.AUTHORIZED
        for d in self.known_defects:
            if d.lifecycle == DefectLifecycle.PROPOSED:
                _move_defect(d, DefectLifecycle.AUTHORIZED)
        return self

    def apply(self, root: Path) -> Mapping[str, Any]:
        root_p = Path(root)
        if self.authorization is None or not self.authorization.granted:
            raise Unauthorized(
                "refusing to apply: no granted authorization. "
                "Warden proposes; a human authorizes."
            )
        if self.status not in {TransformationStatus.AUTHORIZED, TransformationStatus.APPLIED}:
            raise Unauthorized(f"refusing to apply in status {self.status.value}")
        written = []
        for edit in self.edits:
            if Path(edit.path).is_absolute() or not (root_p / edit.path).resolve().is_relative_to(root_p.resolve()):
                raise Unauthorized(f"refusing edit outside the target: {edit.path!r}")
            path = root_p / edit.path
            if edit.kind == "replace":
                if not path.is_file():
                    raise FileNotFoundError(edit.path)
                original = path.read_text(encoding="utf-8")
                if edit.old not in original:
                    raise ValueError(
                        f"{edit.path}: preservation check failed; expected text not found. "
                        "The baseline has drifted; this transformation must be re-proposed."
                    )
                if original.count(edit.old) != 1 and not edit.replace_all:
                    raise ValueError(
                        f"{edit.path}: expected text occurs {original.count(edit.old)} times; "
                        "refusing an ambiguous replace (one intentional change)."
                    )
                new = original.replace(edit.old, edit.new) if edit.replace_all else original.replace(edit.old, edit.new, 1)
                path.write_text(new, encoding="utf-8")
            elif edit.kind == "write":
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(edit.new, encoding="utf-8")
            elif edit.kind == "delete":
                if not path.is_file():
                    raise FileNotFoundError(edit.path)
                path.unlink()
            else:
                raise ValueError(f"unknown edit kind {edit.kind!r}")
            written.append(edit.path)
        self.status = TransformationStatus.APPLIED
        self.result = f"wrote {len(written)} file(s)"
        for d in self.known_defects:
            if d.lifecycle in {DefectLifecycle.AUTHORIZED, DefectLifecycle.PROPOSED}:
                _move_defect(d, DefectLifecycle.MODIFIED)
        return {"written": written, "status": self.status.value}

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "intent": self.intent,
            "architectural_reason": self.architectural_reason,
            "affected_files": list(self.affected_files),
            "expected_behavior": self.expected_behavior,
            "preservation_requirements": list(self.preservation_requirements),
            "known_defects": [
                {
                    "identity": d.identity,
                    "ghost_id": d.ghost_id,
                    "human_id": d.human_id,
                    "summary": d.summary,
                    "severity": d.severity.value,
                    "lifecycle": d.lifecycle.value,
                    "ghost_status": d.ghost_status,
                    "epistemic": d.epistemic.value,
                    "file": d.file,
                    "evidence": list(d.evidence),
                }
                for d in self.known_defects
            ],
            "transformation_scope": self.transformation_scope,
            "baseline_reference": self.baseline_reference,
            "evidence": list(self.evidence),
            "status": self.status.value,
            "authorization": None if self.authorization is None else {
                "actor": self.authorization.actor,
                "operation": self.authorization.operation,
                "subject": self.authorization.subject,
                "scope": self.authorization.scope,
                "reason": self.authorization.reason,
                "granted": self.authorization.granted,
                "at": self.authorization.at,
                "policy_version": self.authorization.policy_version,
            },
            "result": self.result,
        }


@dataclass(frozen=True)
class FileEdit:
    path: str
    kind: str  # "replace" | "write" | "delete"
    new: str
    old: str = ""
    replace_all: bool = False


def defects_from_ghost(findings: Sequence[Mapping[str, Any]]) -> tuple[Defect, ...]:
    """Consume Ghost Tools findings. Preserve their identity. Do not re-hash."""
    out: list[Defect] = []
    counters = {s: 0 for s in DefectSeverity}
    for raw in findings:
        sev = ghost_severity_to_warden(str(raw.get("severity", "minor")))
        counters[sev] += 1
        status = raw.get("status")
        epistemic = EpistemicState.VERIFIED if status == "confirmed" else EpistemicState.UNKNOWN
        if status == "reasoned":
            epistemic = EpistemicState.ASSUMED
        ev = raw.get("evidence") or {}
        out.append(
            Defect(
                summary=str(raw.get("summary", "")),
                severity=sev,
                lifecycle=DefectLifecycle.IDENTIFIED,
                ghost_id=raw.get("id"),
                human_id=human_label(sev, counters[sev]),
                evidence=tuple(filter(None, [raw.get("detail", ""), ev.get("snippet") or ""])),
                file=ev.get("file"),
                epistemic=epistemic,
                ghost_status=status,
                detector=raw.get("detector"),
                line=ev.get("line_start"),
                attributes=dict(raw.get("attributes") or {}),
            )
        )
    return tuple(out)
