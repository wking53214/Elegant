"""Human authority boundary.

Warden proposes. A human (or a governing process acting as one) authorizes.
Nothing in this package treats a proposal as permission.

UNKNOWN is not APPROVED. A missing Authorization is a refusal, not a default.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


class Unauthorized(RuntimeError):
    """A transformation was asked to apply without a granted authorization."""


#: Names that may never authorize a change to Warden's own tree: Warden itself
#: and every other seat or instrument in the stack. Compared in lower case, as a prefix.
SELF_ACTORS = ("warden", "the warden", "drafter", "burnish", "ghost", "ghost_tools",
               "swizzle", "assay", "judge")


def is_stack_actor(actor: str) -> bool:
    """True when `actor` names Warden or another part of the stack (prefix match, any case)."""
    return " ".join(actor.split()).lower().startswith(SELF_ACTORS)


@dataclass(frozen=True)
class Authorization:
    """WHO authorized WHAT, on WHICH subject, for WHICH operation.

    `granted` is the only field that permits a write. An object with
    granted=False is a recorded refusal, not an incomplete yes.
    """

    actor: str
    operation: str
    subject: str
    scope: str
    reason: str
    granted: bool
    at: str
    policy_version: str = "warden-0.1"

    def permits(self, operation: str, subject: str) -> bool:
        return (
            self.granted
            and self.operation == operation
            and self.subject == subject
        )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def refuse(actor: str, operation: str, subject: str, reason: str) -> Authorization:
    return Authorization(
        actor=actor,
        operation=operation,
        subject=subject,
        scope="none",
        reason=reason,
        granted=False,
        at=now_iso(),
    )


def grant(
    actor: str,
    operation: str,
    subject: str,
    scope: str,
    reason: str,
) -> Authorization:
    if not actor.strip() or " ".join(actor.split()).lower() in {"warden", "the warden", "self", "unknown"}:
        raise Unauthorized(
            "Warden cannot authorize its own write. Actor must be a human "
            "or an external governing process, not 'warden' / 'self' / 'unknown'."
        )
    if not reason.strip():
        raise Unauthorized("An authorization without a reason is not an authorization.")
    return Authorization(
        actor=actor.strip(),
        operation=operation,
        subject=subject,
        scope=scope,
        reason=reason.strip(),
        granted=True,
        at=now_iso(),
    )
