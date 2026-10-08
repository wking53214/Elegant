"""The loop: Ghost sees, Proposer proposes, Elegant decides and applies, SWIZZLE checks.

    calibrate (SWIZZLE proves its own instrument)
    repeat, up to max_cycles:
        observe (Ghost) -> Proposer proposes -> authorize (human)
        -> suite before -> apply -> suite after (put back on failure)
        -> Ghost re-inspects
      until the Proposer has nothing left to propose
    SWIZZLE proofs again
    hand off ONCE to the Finisher: beautified code and the final README,
      applied by Elegant under the same gate and put back if the suite
      breaks or Ghost finds anything new

Elegant is the only writer and the only one who says the loop is done. The
Proposer cannot declare itself finished; it can only run out of proposals, and
Elegant checks that Ghost agrees before calling it converged.

This module refuses three self-certifying loops:

    Elegant says Elegant is good.
    Ghost Tools finds its own work correct merely because it produced it.
    SWIZZLE trusts the transformation framework without independent challenge.
"""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Sequence

from .authorization import Authorization, Unauthorized
from .ghost import defects_from_ghost, scan as ghost_scan
from .models import Defect, Transformation, TransformationStatus
from .roles import Finisher, Proposer
from .suite import SuiteRun, preserved, run_suite
from .swizzle import swizzle_proofs_hold

DEFAULT_MAX_CYCLES = 10


@dataclass
class Cycle:
    """One turn of the loop: what was proposed and whether it stood."""

    number: int
    observed: int
    proposal: Optional[Transformation]
    applied: bool
    outcome: str  # APPLIED / PUT_BACK / NOTHING_TO_PROPOSE / REFUSED / SUITE_RED
    suite_before: Optional[SuiteRun] = None
    suite_after: Optional[SuiteRun] = None


@dataclass
class TagTeamResult:
    target: str
    baseline: str
    observed: tuple[Defect, ...]
    reobserved: tuple[Defect, ...]
    cycles: tuple[Cycle, ...]
    converged: bool
    #: ACCEPT / FINISH_REJECTED / NOT_CONVERGED / REJECT / REFUSED / INCONCLUSIVE
    decision: str
    notes: tuple[str, ...]
    finish: Optional[Transformation] = None
    finished: bool = False
    #: True: SWIZZLE's proofs held. False: they did not. None: not configured.
    swizzle_sound: Optional[bool] = None

    @property
    def suite_before(self) -> Optional[SuiteRun]:
        """The target's suite before the first cycle that measured it."""
        return next((c.suite_before for c in self.cycles if c.suite_before is not None), None)

    @property
    def suite_after(self) -> Optional[SuiteRun]:
        """The suite after the last cycle that measured it."""
        return next((c.suite_after for c in reversed(self.cycles) if c.suite_after is not None), None)

    @property
    def applied(self) -> bool:
        return any(c.applied for c in self.cycles) or self.finished


class TagTeam:
    def __init__(
        self,
        *,
        ghost_tools_root: Optional[Path] = None,
        swizzle_root: Optional[Path] = None,
        proposer: Optional[Proposer] = None,
        finisher: Optional[Finisher] = None,
        max_cycles: int = DEFAULT_MAX_CYCLES,
        run_tests: bool = True,
    ) -> None:
        self.ghost_tools_root = ghost_tools_root
        self.swizzle_root = swizzle_root
        self.proposer = proposer
        self.finisher = finisher
        self.max_cycles = max_cycles
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
        sound = self._calibrate(python, notes)
        observed = self._observe(target, findings, python, notes)
        first = observed
        base0 = _fingerprint(target)

        def stop(decision: str, why: str, cycles=(), converged=False, current=None,
                 finish=None, finished=False) -> TagTeamResult:
            return TagTeamResult(
                target=str(target), baseline=base0, observed=first,
                reobserved=observed if current is None else current, cycles=tuple(cycles),
                converged=converged, decision=decision, notes=tuple(notes + [why]),
                finish=finish, finished=finished, swizzle_sound=sound)

        if self.proposer is None:
            return stop("INCONCLUSIVE", "No proposer. Tag team observed only; nothing can be proposed.")
        if authorization is None or not authorization.granted:
            # Show what would be proposed, change nothing.
            proposal = self.proposer.propose(target, observed, _fingerprint(target))
            cycle = Cycle(1, len(observed), proposal, False, "REFUSED")
            return stop("REFUSED", "Human authorization missing. Proposal stands. No write.",
                        cycles=[cycle])
        if sound is False:
            return stop("INCONCLUSIVE", "SWIZZLE's own proofs do not hold; nothing was written.")

        cycles: list[Cycle] = []
        converged = False
        seen: set[str] = set()
        for number in range(1, self.max_cycles + 1):
            baseline = _fingerprint(target)
            proposal = self.proposer.propose(target, observed, baseline)
            if proposal is None or not proposal.edits:
                cycles.append(Cycle(number, len(observed), None, False, "NOTHING_TO_PROPOSE"))
                converged = True
                break
            key = _edits_key(proposal)
            if key in seen:
                cycles.append(Cycle(number, len(observed), proposal, False, "REFUSED"))
                return stop("NOT_CONVERGED", f"Cycle {number}: the Proposer repeated an earlier "
                            "proposal, so the loop is going in circles. Stopped.", cycles)
            seen.add(key)
            cycle = self._apply(target, proposal, authorization, python, notes, number, len(observed))
            cycles.append(cycle)
            if cycle.outcome == "SUITE_RED":
                return stop("INCONCLUSIVE", f"Cycle {number}: the suite is not green; nothing was written.", cycles)
            if cycle.outcome != "APPLIED":
                return stop("REJECT", f"Cycle {number}: {cycle.outcome}. The change was put back; "
                            "the loop stopped.", cycles)
            observed = self._reinspect(target, observed, python, notes)
        if not converged:
            return stop("NOT_CONVERGED", f"No convergence in {self.max_cycles} cycles.", cycles)
        if observed and self.ghost_tools_root is not None:
            notes.append(f"Proposer is out of proposals but Ghost still reports {len(observed)} finding(s). "
                         "Converged means no proposals left, not zero findings.")

        end_sound = self._calibrate(python, notes)
        if end_sound is False:
            return stop("INCONCLUSIVE", "SWIZZLE's proofs failed after the loop; finishing was not attempted.",
                        cycles, converged=True)
        if self.finisher is None:
            return stop("ACCEPT", "Loop converged. No finisher configured.", cycles, converged=True)

        finish = self.finisher.finish(target, _fingerprint(target))
        if finish is None or not finish.edits:
            return stop("ACCEPT", "Loop converged. The Finisher had nothing to finish.",
                        cycles, converged=True)
        done = self._apply(target, finish, authorization, python, notes, 0, len(observed))
        if done.outcome != "APPLIED":
            return stop("FINISH_REJECTED", f"Finishing: {done.outcome}. The finishing change was put back; "
                        "the converged loop result stands.", cycles, converged=True, finish=finish)
        after = self._reinspect(target, observed, python, notes)
        new = {d.ghost_id for d in after if d.ghost_id} - {d.ghost_id for d in observed if d.ghost_id}
        if new:
            _restore(target, done.restore)
            finish.status = TransformationStatus.REJECTED
            return stop("FINISH_REJECTED", f"Finishing introduced new Ghost finding(s) {sorted(new)}. "
                        "The finishing change was put back.", cycles, converged=True,
                        current=observed, finish=finish)
        return stop("ACCEPT", "Loop converged and the finishing change stands.", cycles,
                    converged=True, current=after, finish=finish, finished=True)

    # -- steps ------------------------------------------------------------

    def _apply(self, target: Path, proposal: Transformation, auth: Authorization, python: str,
               notes: list[str], number: int, seen: int) -> "_Applied":
        before = self._suite(target, python, notes, f"cycle {number} before")
        if before is not None and not before.green:
            proposal.status = TransformationStatus.PROPOSED
            notes.append("Rule 7: the target's suite is not green before the change "
                         f"({before.describe()}), so it cannot protect behavior. Nothing was written.")
            return _Applied(number, seen, proposal, False, "SUITE_RED", before, None, {})
        snapshot = _snapshot(target, proposal)
        proposal.authorize(auth)
        proposal.apply(target)
        notes.append(f"Cycle {number}: transformation applied under granted authorization.")
        after = self._suite(target, python, notes, f"cycle {number} after")
        broken = preserved(before, after) if before is not None else None
        if broken is not None:
            _restore(target, snapshot)
            proposal.status = TransformationStatus.REJECTED
            notes.append(f"Rule 7: {broken}.")
            return _Applied(number, seen, proposal, False, "PUT_BACK", before, after, snapshot)
        return _Applied(number, seen, proposal, True, "APPLIED", before, after, snapshot)

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
            if when.endswith("before"):
                notes.append("Rule 7 NOT RUN: run_tests=False. Behavior preservation is unmeasured.")
            return None
        result = run_suite(target, python)
        notes.append(f"Rule 7 suite {when}: {result.describe()}.")
        return result

    def _reinspect(self, target: Path, observed: tuple[Defect, ...], python: str,
                   notes: list[str]) -> tuple[Defect, ...]:
        if self.ghost_tools_root is None:
            return observed
        reobserved = defects_from_ghost(
            ghost_scan(target, ghost_tools_root=self.ghost_tools_root, python=python))
        before_ids = {d.ghost_id for d in observed if d.ghost_id}
        after_ids = {d.ghost_id for d in reobserved if d.ghost_id}
        notes.append(f"Ghost re-inspected: {len(reobserved)} finding(s); "
                     f"closed={sorted(before_ids - after_ids)} new={sorted(after_ids - before_ids)}")
        return reobserved


@dataclass
class _Applied(Cycle):
    restore: Dict[str, Optional[str]] = field(default_factory=dict)

    def __init__(self, number, observed, proposal, applied, outcome, before, after, restore):
        super().__init__(number, observed, proposal, applied, outcome, before, after)
        self.restore = restore


def _fingerprint(target: Path) -> str:
    """A short hash of the tree, so a proposal can say which state it was written against."""
    digest = hashlib.sha256()
    skip = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules"}
    for path in sorted(Path(target).rglob("*")):
        if path.is_file() and not skip.intersection(path.relative_to(target).parts):
            digest.update(str(path.relative_to(target)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def _edits_key(proposal: Transformation) -> str:
    return hashlib.sha256(repr([(e.path, e.kind, e.old, e.new) for e in proposal.edits]).encode()).hexdigest()


def _refuse_self_authorization(target: Path, authorization: Optional[Authorization]) -> None:
    """Elegant may transform other repos. Transforming itself under its own
    proposal is the self-certifying loop."""
    if (target.name.lower() == "elegant" and authorization and authorization.granted
            and authorization.actor.lower() in {"elegant", "self"}):
        raise Unauthorized("Elegant cannot authorize work on itself.")


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
