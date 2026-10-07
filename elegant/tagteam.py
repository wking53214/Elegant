"""Ghost Tools × Elegant × SWIZZLE tag team.

Conceptual order (starting hypothesis, implemented as this module):

    observe (Ghost) → propose (Elegant) → authorize (human)
        → transform → re-inspect (Ghost) → attack (SWIZZLE-style oracle)
        → ACCEPT / REJECT

This module refuses three self-certifying loops:

    Elegant says Elegant is good.
    Ghost Tools finds its own work correct merely because it produced it.
    SWIZZLE trusts the transformation framework without independent challenge.

The documentation-honesty oracle in elegant.swizzle does not import the
critic, and the critic does not import the oracle.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Sequence

from .authorization import Authorization, Unauthorized
from .critic import PoetryCritic, CriticReport
from .ghost import defects_from_ghost, scan as ghost_scan
from .models import Defect, Transformation, TransformationStatus
from .narrative import inspect_tree
from .swizzle import (AttackResult, GroundTruth, attack_documentation_honesty, freeze,
                      swizzle_proofs_hold)


@dataclass
class TagTeamResult:
    target: str
    baseline: str
    observed: tuple[Defect, ...]
    proposal: Optional[Transformation]
    applied: bool
    reobserved: tuple[Defect, ...]
    attack: Optional[AttackResult]
    critic_before: CriticReport
    critic_after: Optional[CriticReport]
    decision: str  # ACCEPT / REJECT / REFUSED / INCONCLUSIVE
    notes: tuple[str, ...]
    #: True: SWIZZLE's proofs held. False: they did not (no write happens).
    #: None: SWIZZLE was not configured, which the notes say out loud.
    swizzle_sound: Optional[bool] = None


class TagTeam:
    def __init__(
        self,
        *,
        ghost_tools_root: Optional[Path] = None,
        swizzle_root: Optional[Path] = None,
        proposer: Optional[Callable[[Path, tuple[Defect, ...], GroundTruth], Transformation]] = None,
    ) -> None:
        self.ghost_tools_root = ghost_tools_root
        self.swizzle_root = swizzle_root
        self.proposer = proposer
        self.critic = PoetryCritic()

    def run(
        self,
        target: Path,
        *,
        authorization: Optional[Authorization] = None,
        findings: Optional[Sequence[dict]] = None,
        python: str = "",
    ) -> TagTeamResult:
        target = Path(target).resolve()
        notes: list[str] = []
        if Path(target).name.lower() == "elegant" and authorization and authorization.granted:
            # Elegant may transform other repos. Transforming *itself* under
            # its own proposal is the self-certifying loop.
            if authorization.actor.lower() in {"elegant", "self"}:
                raise Unauthorized("Elegant cannot authorize work on itself.")

        # SWIZZLE's instrument check: are its own planted defects still real?
        # Run once per loop, recorded either way, and required for ACCEPT.
        swizzle_sound: Optional[bool] = None
        if self.swizzle_root is not None:
            import sys
            swizzle_sound, summary = swizzle_proofs_hold(
                swizzle_root=self.swizzle_root, python=python or sys.executable)
            notes.append(summary)
        else:
            notes.append("SWIZZLE proofs NOT RUN: no swizzle_root. The adversary is uncalibrated.")

        nar = inspect_tree(target)
        critic_before = self.critic.critique(target, nar)
        ground = freeze(target)

        if findings is None:
            if self.ghost_tools_root is None:
                observed: tuple[Defect, ...] = ()
                notes.append("Ghost Tools scan SKIPPED: no ghost_tools_root. Observation is UNKNOWN.")
            else:
                import sys
                py = python or sys.executable
                raw = ghost_scan(target, ghost_tools_root=self.ghost_tools_root, python=py)
                findings = list(raw)
                observed = defects_from_ghost(raw)
                notes.append(f"Ghost Tools observed {len(observed)} finding(s).")
        else:
            observed = defects_from_ghost(findings)
            notes.append(f"Ghost Tools findings loaded ({len(observed)}), not scanned in this process.")

        if self.proposer is None:
            return TagTeamResult(
                target=str(target),
                baseline=ground.readme_sha16,
                observed=observed,
                proposal=None,
                applied=False,
                reobserved=(),
                attack=None,
                critic_before=critic_before,
                critic_after=None,
                decision="INCONCLUSIVE",
                notes=tuple(notes + ["No proposer. Tag team observed and criticised only."]),
                swizzle_sound=swizzle_sound,
            )

        proposal = self.proposer(target, observed, ground)
        if authorization is None or not authorization.granted:
            proposal.status = TransformationStatus.PROPOSED
            return TagTeamResult(
                target=str(target),
                baseline=ground.readme_sha16,
                observed=observed,
                proposal=proposal,
                applied=False,
                reobserved=(),
                attack=None,
                critic_before=critic_before,
                critic_after=None,
                decision="REFUSED",
                notes=tuple(notes + ["Human authorization missing. Proposal stands. No write."]),
                swizzle_sound=swizzle_sound,
            )

        if swizzle_sound is False:
            # Stop before the write: an adversary whose own proofs fail
            # cannot judge the change afterwards, so the change is not made.
            proposal.status = TransformationStatus.PROPOSED
            return TagTeamResult(
                target=str(target),
                baseline=ground.readme_sha16,
                observed=observed,
                proposal=proposal,
                applied=False,
                reobserved=(),
                attack=None,
                critic_before=critic_before,
                critic_after=None,
                decision="INCONCLUSIVE",
                notes=tuple(notes + ["SWIZZLE's own proofs do not hold; nothing was written."]),
                swizzle_sound=False,
            )

        proposal.authorize(authorization)
        proposal.apply(target)
        notes.append("Transformation applied under granted authorization.")

        reobserved: tuple[Defect, ...] = ()
        if self.ghost_tools_root is not None:
            import sys
            py = python or sys.executable
            raw2 = ghost_scan(target, ghost_tools_root=self.ghost_tools_root, python=py)
            reobserved = defects_from_ghost(raw2)
            notes.append(f"Ghost Tools re-inspected: {len(reobserved)} finding(s).")
            before_ids = {d.ghost_id for d in observed if d.ghost_id}
            after_ids = {d.ghost_id for d in reobserved if d.ghost_id}
            notes.append(
                f"finding-id delta: closed={sorted(before_ids - after_ids)} "
                f"new={sorted(after_ids - before_ids)}"
            )

        attack = attack_documentation_honesty(target, ground)
        critic_after = self.critic.critique(target)
        if attack.judgement == "REJECT":
            decision = "REJECT"
        elif attack.judgement == "INCONCLUSIVE":
            decision = "INCONCLUSIVE"
        elif not critic_after.good_enough:
            decision = "REJECT"
            notes.append("Oracle accepted test-count honesty; critic still says this isn't good enough yet.")
        else:
            decision = "ACCEPT"

        return TagTeamResult(
            target=str(target),
            baseline=ground.readme_sha16,
            observed=observed,
            proposal=proposal,
            applied=True,
            reobserved=reobserved,
            attack=attack,
            critic_before=critic_before,
            critic_after=critic_after,
            decision=decision,
            notes=tuple(notes),
            swizzle_sound=swizzle_sound,
        )
