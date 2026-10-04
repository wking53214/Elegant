"""Elegant: architectural transparency for a specialized corpus.

WHAT THIS IS
    A software-writing system. The source is the primary artifact. Documentation
    is architectural infrastructure, not a coat of paint.

WHAT IT OWNS
    Transformation proposals, the poetry critic, README compilation from
    source narrative, the human authorization boundary, and the tag-team
    orchestration that *calls* Ghost Tools and SWIZZLE without becoming them.

WHAT IT DOES NOT OWN
    Forensic inspection (Ghost Tools). Adversarial challenge (SWIZZLE).
    Runtime governance contracts (CNS). Live admission, decision, custody.

WHAT IT MUST NEVER DO
    Silently alter code.
    Score beauty.
    Certify itself.
    Modify CNS.
    Convert UNKNOWN into APPROVED.
    Claim a test passed that was not executed.
    Hide a defect under better prose.

The museum test: a competent programmer should be able to read the source
and understand the conceptual architecture without having to execute every
pathway merely to discover what the code is trying to do. Execution still
determines whether the architectural story is true.
"""

from .epistemic import EpistemicState
from .models import Defect, DefectLifecycle, Transformation, TransformationStatus
from .authorization import Authorization, Unauthorized
from .critic import PoetryCritic, CriticReport
from .narrative import Narrative, inspect_tree
from .tagteam import TagTeam, TagTeamResult

__version__ = "0.1.0"

__all__ = [
    "EpistemicState",
    "Defect",
    "DefectLifecycle",
    "Transformation",
    "TransformationStatus",
    "Authorization",
    "Unauthorized",
    "PoetryCritic",
    "CriticReport",
    "Narrative",
    "inspect_tree",
    "TagTeam",
    "TagTeamResult",
    "__version__",
]
