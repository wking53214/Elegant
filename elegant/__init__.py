"""Elegant: the discipline of change.

WHAT THIS IS
    The governor of a code change. It decides whether a change may be made,
    whether it stands, and what is recorded. It does not decide what makes code
    beautiful; that is Streamline's work, and it reaches Elegant through the
    `Craft` interface in `elegant.craft`.

WHAT IT OWNS
    Transformation proposals as data, the human authorization boundary, the
    Rule 7 test gate, the Rule 9 audit file, the SWIZZLE proof gate, and the
    tag-team loop that *calls* Ghost Tools, SWIZZLE and a craft without
    becoming any of them.

WHAT IT DOES NOT OWN
    The opinion about better code (Streamline). Forensic inspection (Ghost
    Tools). Adversarial challenge (SWIZZLE). Runtime governance contracts
    (CNS). Live admission, decision, custody.

WHAT IT MUST NEVER DO
    Silently alter code.
    Certify itself.
    Modify CNS.
    Convert UNKNOWN into APPROVED.
    Let a craft's good opinion outvote a red suite or a missing grant.
"""

from .epistemic import EpistemicState
from .models import Defect, DefectLifecycle, Transformation, TransformationStatus
from .authorization import Authorization, Unauthorized
from .craft import AttackResult, Craft, Review
from .tagteam import TagTeam, TagTeamResult
from .horsemen import HorsemenWorkflow, ChangeClass, ScopedGrant

__version__ = "0.4.0"

__all__ = [
    "EpistemicState",
    "Defect",
    "DefectLifecycle",
    "Transformation",
    "TransformationStatus",
    "Authorization",
    "Unauthorized",
    "AttackResult",
    "Craft",
    "Review",
    "TagTeam",
    "TagTeamResult",
    "HorsemenWorkflow",
    "ChangeClass",
    "ScopedGrant",
    "__version__",
]
