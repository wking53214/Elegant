"""Ghost Tools × Elegant × SWIZZLE tag team: the discipline of change.

Conceptual order (implemented as this module):

    calibrate (SWIZZLE proves its own instrument)
        → observe (Ghost) → propose (a craft) → authorize (human)
        → suite before (Rule 7) → transform → suite after (Rule 7)
        → re-inspect (Ghost) → attack (the craft's independent oracle)
        → ACCEPT / REJECT

What counts as better is not decided here. A craft (see `elegant.craft`;
Streamline is the one that exists) answers freeze, review, propose and attack.
This module decides only whether a change may be made and whether it stands.

Every stop before the write returns the same shape through `_stopped`, so
the reason a run ended is always one sentence in the notes and nothing is
written. A change that breaks the target's suite is put back.

This module refuses three self-certifying loops:

    Elegant says Elegant is good.
    Ghost Tools finds its own work correct merely because it produced it.
    SWIZZLE trusts the transformation framework without independent challenge.

A craft's own reviewer and its attack oracle are separate questions asked
separately; a good review never outvotes a failed suite or a failed attack.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Sequence

from .authorization import Authorization, Unauthorized
from .craft import AttackResult, Craft, Review
from .ghost import defects_from_ghost, scan as ghost_scan
from .models import Defect, Transformation, TransformationStatus
from .suite import SuiteRun, preserved, run_suite
from .swizzle import swizzle_proofs_hold


@dataclass
class TagTeamResult:
    target: str
    baseline: str
    observed: tuple[Defect, ...]
    proposal: Optional[Transformation]
    applied: bool
    reobserved: tuple[Defect, ...]
    attack: Optional[AttackResult]
    review_before: Optional[Review]
    review_after: Optional[Review]
    decision: str  # ACCEPT / REJECT / REFUSED / INCONCLUSIVE
    notes: tuple[str, ...]
    #: True: SWIZZLE's proofs held. False: they did not (no write happens).
    #: None: SWIZZLE was not configured, which the notes say out loud.
    swizzle_sound: Optional[bool] = None
    #: Rule 7: the target's suite before and after the change, as measured.
    suite_before: Optional[SuiteRun] = None
    suite_after: Optional[SuiteRun] = None


class TagTeam:
    def __init__(
        self,
        *,
        ghost_tools_root: Optional[Path] = None,
        swizzle_root: Optional[Path] = None,
        craft: Optional[Craft] = None,
        run_tests: bool = True,
    ) -> None:
        self.ghost_tools_root = ghost_tools_root
        self.swizzle_root = swizzle_root
        self.craft = craft
        #: Rule 7. Off only for callers that measure the suite some other way;
        #: the notes say so when it is off.
        self.run_tests = run_tests

    def run(
        self,
        target: Path,
        *,
        authorization: Optional[Authorization] = None,
        findings: Optional[Sequence[dict]] = None,
        python: str = "",
    ) -> TagTeamResult:
        target = Path(target).resolve()
        python = python or sys.executable
        _refuse_self_authorization(target, authorization)
        notes: list[str] = []
        swizzle_sound = self._calibrate(python, notes)
        observed = self._observe(target, findings, python, notes)
        craft = self.craft
        if craft is None:
            common = dict(target=str(target), baseline="UNKNOWN", observed=observed,
                          review_before=None, swizzle_sound=swizzle_sound)
            return _stopped(common, notes, "INCONCLUSIVE",
                            "No craft. Tag team observed only; nothing can be proposed.")
        ground = craft.freeze(target)
        common = dict(target=str(target), baseline=ground.fingerprint, observed=observed,
                      review_before=craft.review(target), swizzle_sound=swizzle_sound)
        proposal = craft.propose(target, observed, ground)
        if authorization is None or not authorization.granted:
            proposal.status = TransformationStatus.PROPOSED
            return _stopped(common, notes, "REFUSED",
                            "Human authorization missing. Proposal stands. No write.", proposal)
        if swizzle_sound is False:
            # An adversary whose own proofs fail cannot judge the change
            # afterwards, so the change is not made.
            proposal.status = TransformationStatus.PROPOSED
            return _stopped(common, notes, "INCONCLUSIVE",
                            "SWIZZLE's own proofs do not hold; nothing was written.", proposal)

        before = self._suite(target, python, notes, "before")
        if before is not None and not before.green:
            proposal.status = TransformationStatus.PROPOSED
            return _stopped(common, notes, "INCONCLUSIVE",
                            "Rule 7: the target's suite is not green before the change "
                            f"({before.describe()}), so it cannot protect behavior. Nothing was written.",
                            proposal, suite_before=before)

        snapshot = _snapshot(target, proposal)
        proposal.authorize(authorization)
        proposal.apply(target)
        notes.append("Transformation applied under granted authorization.")

        after = self._suite(target, python, notes, "after")
        broken = preserved(before, after) if before is not None else None
        if broken is not None:
            _restore(target, snapshot)
            proposal.status = TransformationStatus.REJECTED
            return _stopped(common, notes, "REJECT",
                            f"Rule 7: {broken}. The change was put back.",
                            proposal, suite_before=before, suite_after=after)

        reobserved = self._reinspect(target, observed, python, notes)
        attack = craft.attack(target, ground)
        review_after = craft.review(target)
        return TagTeamResult(
            **common, proposal=proposal, applied=True, reobserved=reobserved, attack=attack,
            review_after=review_after, decision=_decide(attack, review_after, notes),
            notes=tuple(notes), suite_before=before, suite_after=after,
        )

    # -- steps ------------------------------------------------------------

    def _calibrate(self, python: str, notes: list[str]) -> Optional[bool]:
        """SWIZZLE's instrument check: are its own planted defects still real?"""
        if self.swizzle_root is None:
            notes.append("SWIZZLE proofs NOT RUN: no swizzle_root. The adversary is uncalibrated.")
            return None
        sound, summary = swizzle_proofs_hold(swizzle_root=self.swizzle_root, python=python)
        notes.append(summary)
        return sound

    def _observe(self, target: Path, findings: Optional[Sequence[dict]], python: str,
                 notes: list[str]) -> tuple[Defect, ...]:
        if findings is not None:
            observed = defects_from_ghost(findings)
            notes.append(f"Ghost Tools findings loaded ({len(observed)}), not scanned in this process.")
            return observed
        if self.ghost_tools_root is None:
            notes.append("Ghost Tools scan SKIPPED: no ghost_tools_root. Observation is UNKNOWN.")
            return ()
        observed = defects_from_ghost(
            ghost_scan(target, ghost_tools_root=self.ghost_tools_root, python=python))
        notes.append(f"Ghost Tools observed {len(observed)} finding(s).")
        return observed

    def _suite(self, target: Path, python: str, notes: list[str], when: str) -> Optional[SuiteRun]:
        if not self.run_tests:
            if when == "before":
                notes.append("Rule 7 NOT RUN: run_tests=False. Behavior preservation is unmeasured.")
            return None
        result = run_suite(target, python)
        notes.append(f"Rule 7 suite {when}: {result.describe()}.")
        return result

    def _reinspect(self, target: Path, observed: tuple[Defect, ...], python: str,
                   notes: list[str]) -> tuple[Defect, ...]:
        if self.ghost_tools_root is None:
            return ()
        reobserved = defects_from_ghost(
            ghost_scan(target, ghost_tools_root=self.ghost_tools_root, python=python))
        notes.append(f"Ghost Tools re-inspected: {len(reobserved)} finding(s).")
        before_ids = {d.ghost_id for d in observed if d.ghost_id}
        after_ids = {d.ghost_id for d in reobserved if d.ghost_id}
        notes.append(f"finding-id delta: closed={sorted(before_ids - after_ids)} "
                     f"new={sorted(after_ids - before_ids)}")
        return reobserved


def _refuse_self_authorization(target: Path, authorization: Optional[Authorization]) -> None:
    """Elegant may transform other repos. Transforming itself under its own
    proposal is the self-certifying loop."""
    if (target.name.lower() == "elegant" and authorization and authorization.granted
            and authorization.actor.lower() in {"elegant", "self"}):
        raise Unauthorized("Elegant cannot authorize work on itself.")


def _stopped(common: dict, notes: list[str], decision: str, reason: str,
             proposal: Optional[Transformation] = None, **suites) -> TagTeamResult:
    """A run that ends without an accepted write: one shape, one stated reason."""
    return TagTeamResult(**common, proposal=proposal, applied=False, reobserved=(), attack=None,
                         review_after=None, decision=decision, notes=tuple(notes + [reason]),
                         **suites)


def _decide(attack: AttackResult, review_after: Review, notes: list[str]) -> str:
    if attack.judgement in {"REJECT", "INCONCLUSIVE"}:
        return attack.judgement
    if not review_after.good_enough:
        notes.append("The oracle accepted the change; the craft's review still says it is not good enough yet.")
        return "REJECT"
    return "ACCEPT"


def _snapshot(target: Path, proposal: Transformation) -> Dict[str, Optional[str]]:
    """Each file the proposal touches, as it is now (None: it does not exist yet)."""
    out: Dict[str, Optional[str]] = {}
    for edit in proposal.edits:
        path = target / edit.path
        out[edit.path] = path.read_text(encoding="utf-8") if path.is_file() else None
    return out


def _restore(target: Path, snapshot: Dict[str, Optional[str]]) -> None:
    for rel, text in snapshot.items():
        path = target / rel
        if text is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(text, encoding="utf-8")
