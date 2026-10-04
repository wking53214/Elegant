"""Truthful epistemic language.

Elegant uses this vocabulary for *its own* claims about architecture and
documentation. When Ghost Tools already has a stronger native vocabulary
(CONFIRMED / REASONED / SUPPRESSED), Elegant preserves that vocabulary on
consumed findings and does not rename it for cosmetic consistency.

These states are not a confidence score. They are a contract about what
kind of evidence exists.
"""

from __future__ import annotations

from enum import Enum


class EpistemicState(str, Enum):
    """What kind of claim is being made.

    GUARANTEED     the code plus an invariant make any other outcome a bug
    VERIFIED       an executed check established this, on this run
    IMPLEMENTED    the source contains the behaviour; it may be untested
    DESIGNED       intended; not the same as implemented
    ASSUMED        taken as true without a check in this artifact
    UNKNOWN        evidence is insufficient; this is a valid result
    NOT_IMPLEMENTED
    INTENTIONALLY_NOT_PROVIDED
    """

    GUARANTEED = "guaranteed"
    VERIFIED = "verified"
    IMPLEMENTED = "implemented"
    DESIGNED = "designed"
    ASSUMED = "assumed"
    UNKNOWN = "unknown"
    NOT_IMPLEMENTED = "not_implemented"
    INTENTIONALLY_NOT_PROVIDED = "intentionally_not_provided"


# Ghost Tools forensic vocabulary, consumed not replaced.
GHOST_STATUS = frozenset({"confirmed", "reasoned", "confirmed_by_review", "rejected", "suppressed"})
