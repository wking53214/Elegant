"""The loop: Ghost sees, Drafter proposes, Warden decides and applies, SWIZZLE checks.

    calibrate (SWIZZLE proves its own instrument)
    repeat, up to max_cycles:
        observe (Ghost) -> Drafter proposes -> authorize (human)
        -> suite before -> apply -> suite after (put back on failure)
        -> Ghost re-inspects
      until the Drafter has nothing left to propose
    SWIZZLE proofs again
    hand off ONCE to the Finisher: beautified code and the final README,
      applied by Warden under the same gate and put back if the suite
      breaks or Ghost finds anything new

Warden is the only writer and the only one who says the loop is done. The
Drafter cannot declare itself finished; it can only run out of proposals, and
Warden checks that Ghost agrees before calling it converged.

This module refuses three self-certifying loops:

    Warden says Warden is good.
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
from .deletion import commented_variant, is_deletion, keep_variant, stamp_now
from .ghost import defects_from_ghost, scan as ghost_scan
from .guard import SeatBrokeCharter, Snapshot, is_protected, violation, watch
from .models import Defect, FileEdit, Transformation, TransformationStatus
from .roles import Evidence, Facts, Finisher, Drafter, Judge, Verdict
from .suite import SuiteRun, preserved, run_suite
from .swizzle import governor_attacks, swizzle_proofs_hold

DEFAULT_MAX_CYCLES = 10


class GhostUnavailable(RuntimeError):
    """Ghost could not be run or its output could not be read. UNKNOWN, not zero findings."""


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
    #: Checks that did not run. A non-empty value turns ACCEPT into ACCEPT_UNVERIFIED.
    unmeasured: tuple[str, ...] = ()
    #: What the Judge said, when one was seated.
    verdict: Optional[Verdict] = None

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
        drafter: Optional[Drafter] = None,
        finisher: Optional[Finisher] = None,
        judge: Optional[Judge] = None,
        max_cycles: int = DEFAULT_MAX_CYCLES,
        run_tests: bool = True,
    ) -> None:
        self.ghost_tools_root = ghost_tools_root
        self.swizzle_root = swizzle_root
        self.drafter = drafter
        self.finisher = finisher
        self.judge = judge
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
        _refuse_self_authorization(target, authorization)
        self._notes: list[str] = []
        self._trail: list[Cycle] = []
        try:
            return self._run(target, authorization, findings, python or sys.executable)
        except (SeatBrokeCharter, GhostUnavailable) as err:
            decision = "REJECT" if isinstance(err, SeatBrokeCharter) else "INCONCLUSIVE"
            return TagTeamResult(
                target=str(target), baseline="", observed=(), reobserved=(),
                cycles=tuple(self._trail), converged=False, decision=decision,
                notes=tuple(self._notes + [str(err)]), unmeasured=self._unmeasured(None))

    def _judge(self, target, authorization, cycles, first, current, finish, finished, sound,
               declined, python, notes, start):
        """Hand the evidence to the Judge. Only the Judge can turn a run into ACCEPT.

        REJECT puts the whole tree back as it was found. Anything the Judge
        cannot decide, or fails at, leaves the changes standing but unjudged.
        """
        edits = [(e.path, e.kind) for c in cycles if c.applied and c.proposal for e in c.proposal.edits]
        if finished and finish is not None:
            edits += [(e.path, e.kind) for e in finish.edits]
        attacks = None
        if self.swizzle_root is not None and sound is True:
            import warden
            attacks = governor_attacks(swizzle_root=self.swizzle_root,
                                       warden_root=Path(warden.__file__).resolve().parents[1], python=python)
            notes.append("SWIZZLE attacks on the governor: "
                         + ("not run" if attacks is None else
                            f"{sum(a['status'] == 'violated' for a in attacks)} of {len(attacks)} violated"))
        suite_after = self._suite(target, python, notes, "final state, for the Judge")
        first_suite = next((c.suite_before for c in cycles if c.suite_before is not None), None)
        ghost = self.ghost_tools_root is not None
        evidence = Evidence(
            target=str(target), scope=authorization.scope if authorization else "",
            cycles=tuple((c.number, c.outcome) for c in cycles), changed=tuple(edits),
            judging_files_touched=tuple(sorted({p for p, _ in edits if is_protected(p)})),
            suite_before=first_suite if first_suite is not None else suite_after, suite_after=suite_after,
            ghost_before=tuple(sorted(d.identity for d in first)) if ghost else None,
            ghost_after=tuple(sorted(d.identity for d in current)) if ghost else None,
            declined=tuple(sorted(declined)), swizzle_proofs=sound, attacks=attacks,
            unmeasured=self._unmeasured(sound), notes=tuple(notes))
        try:
            with watch(target, "The Judge"):
                verdict = self.judge.decide(evidence)
        except SeatBrokeCharter:
            raise
        except Exception as err:  # noqa: BLE001 - a judge that fails has not approved anything
            notes.append(f"The Judge failed ({type(err).__name__}); nothing was approved.")
            return "ACCEPT_UNVERIFIED", None, " The Judge failed, so this is not approved."
        said = "; ".join(verdict.reasons) or "no reasons given"
        if verdict.decision == "ACCEPT":
            return "ACCEPT", verdict, f" Judge: ACCEPT ({said})."
        if verdict.decision == "REJECT":
            undone = ""
            if start is not None and start.restorable:
                start.restore()
                undone = " The whole tree was put back as it was found."
            elif start is not None:
                undone = " The tree was too large to restore automatically."
            return "JUDGE_REJECTED", verdict, f" Judge: REJECT ({said}).{undone}"
        return "ACCEPT_UNVERIFIED", verdict, f" Judge: INSUFFICIENT ({said}). The changes stand, unjudged."

    def _unmeasured(self, sound: Optional[bool]) -> tuple[str, ...]:
        out = []
        if self.ghost_tools_root is None:
            out.append("ghost")
        if self.swizzle_root is None or sound is False:
            out.append("swizzle")
        if not self.run_tests:
            out.append("suite")
        if self.judge is None:
            out.append("judge")
        return tuple(out)

    def _run(self, target: Path, authorization: Optional[Authorization],
             findings: Optional[Sequence[dict]], python: str) -> TagTeamResult:
        notes = self._notes
        sound = self._calibrate(python, notes)
        observed = self._observe(target, findings, python, notes)
        first = observed
        base0 = _fingerprint(target)
        start = Snapshot(target) if self.judge is not None else None
        declined: set[str] = set()

        def stop(decision: str, why: str, cycles=(), converged=False, current=None,
                 finish=None, finished=False) -> TagTeamResult:
            missing = self._unmeasured(sound)
            candidate = decision == "ACCEPT"
            gaps = tuple(m for m in missing if m != "judge")
            if candidate and missing:
                decision = "ACCEPT_UNVERIFIED"
                why += f" Not measured: {', '.join(missing)}. Nothing here says those checks would have passed."
            verdict = None
            reobserved = observed if current is None else current
            if candidate and self.judge is not None:
                judged, verdict, extra = self._judge(
                    target, authorization, tuple(cycles), first, reobserved, finish, finished,
                    sound, declined, python, notes, start)
                why += extra
                # Whatever the Judge says, a run with gaps in its measurements is not a plain ACCEPT.
                decision = "ACCEPT_UNVERIFIED" if judged == "ACCEPT" and gaps else judged
            return TagTeamResult(
                target=str(target), baseline=base0, observed=first,
                reobserved=reobserved, cycles=tuple(cycles),
                converged=converged, decision=decision, notes=tuple(notes + [why]),
                finish=finish, finished=finished, swizzle_sound=sound, unmeasured=missing,
                verdict=verdict)

        if self.drafter is None:
            return stop("INCONCLUSIVE", "No drafter. Tag team observed only; nothing can be proposed.")
        if authorization is None or not authorization.granted:
            # Show what would be proposed, change nothing.
            with watch(target, "The Drafter"):
                proposal = self.drafter.propose(target, observed, _fingerprint(target))
            cycle = Cycle(1, len(observed), proposal, False, "REFUSED")
            return stop("REFUSED", "Human authorization missing. Proposal stands. No write.",
                        cycles=[cycle])
        if sound is False:
            return stop("INCONCLUSIVE", "SWIZZLE's own proofs do not hold; nothing was written.")

        cycles: list[Cycle] = self._trail
        converged = False
        seen: set[str] = set()
        #: Findings whose removal failed a test (`declined`) are not offered to the Drafter again.
        for number in range(1, self.max_cycles + 1):
            baseline = _fingerprint(target)
            offered = tuple(d for d in observed if d.identity not in declined)
            with watch(target, "The Drafter"):
                proposal = self.drafter.propose(target, offered, baseline)
            if proposal is None or not proposal.edits:
                cycles.append(Cycle(number, len(observed), None, False, "NOTHING_TO_PROPOSE"))
                converged = True
                break
            key = _edits_key(proposal)
            bad = violation(target, proposal, authorization)
            if bad:
                kind, why = bad
                if kind == "escape" or not proposal.known_defects:
                    cycles.append(Cycle(number, len(observed), proposal, False, "REFUSED"))
                    return stop("REJECT", f"Cycle {number}: {why}. Nothing was written.", cycles)
                declined.update(d.identity for d in proposal.known_defects)
                cycles.append(Cycle(number, len(observed), proposal, False, "DECLINED"))
                notes.append(f"Cycle {number}: change declined. {why}.")
                continue
            removes = is_deletion(target, proposal)
            if removes:
                scope, why = self._keep_test(target, proposal, observed, python, notes, number)
                if scope == "systemic":
                    cycles.append(Cycle(number, len(observed), proposal, False, "REFUSED"))
                    return stop("REJECT", f"Cycle {number}: the removal was not applied. {why}", cycles)
                original = proposal
                proposal = None if scope else _commented(target, proposal)
                if proposal is None:
                    why = why or "The removed code could not be commented out precisely."
                    declined.update(d.identity for d in original.known_defects)
                    cycles.append(Cycle(number, len(observed), original, False, "DECLINED"))
                    notes.append(f"Cycle {number}: removal declined, code left as it is. {why}")
                    continue
                key = _edits_key(proposal)
            if key in seen:
                cycles.append(Cycle(number, len(observed), proposal, False, "REFUSED"))
                return stop("NOT_CONVERGED", f"Cycle {number}: the Drafter repeated an earlier "
                            "proposal, so the loop is going in circles. Stopped.", cycles)
            seen.add(key)
            cycle = self._apply(target, proposal, authorization, python, notes, number,
                                len(observed))
            cycles.append(cycle)
            if cycle.outcome == "SUITE_RED":
                return stop("INCONCLUSIVE", f"Cycle {number}: the suite is not green; nothing was written.", cycles)
            if cycle.outcome != "APPLIED":
                return stop("REJECT", f"Cycle {number}: {cycle.outcome}. The change was put back; "
                            "the loop stopped.", cycles)
            after = self._reinspect(target, observed, python, notes)
            new = {d.ghost_id for d in after if d.ghost_id} - {d.ghost_id for d in observed if d.ghost_id}
            if removes and new:
                _restore(target, cycle.restore)
                proposal.status = TransformationStatus.REJECTED
                cycle.applied, cycle.outcome = False, "DECLINED"
                declined.update(d.identity for d in proposal.known_defects)
                notes.append(f"Cycle {number}: comment-out test failed. The change produced new Ghost "
                             f"finding(s) {sorted(new)}; it was put back and the code left as it is.")
                continue
            observed = after
        if not converged:
            return stop("NOT_CONVERGED", f"No convergence in {self.max_cycles} cycles.", cycles)
        if declined:
            notes.append(f"Removals declined and left in place: {sorted(declined)}.")
        if observed and self.ghost_tools_root is not None:
            notes.append(f"Drafter is out of proposals but Ghost still reports {len(observed)} finding(s). "
                         "Converged means no proposals left, not zero findings.")

        end_sound = self._calibrate(python, notes)
        if end_sound is False:
            return stop("INCONCLUSIVE", "SWIZZLE's proofs failed after the loop; finishing was not attempted.",
                        cycles, converged=True)
        if self.finisher is None:
            return stop("ACCEPT", "Loop converged. No finisher configured.", cycles, converged=True)

        facts = Facts(suite=self._suite(target, python, notes, "converged"),
                      remaining=observed, cycles=len([c for c in cycles if c.applied]),
                      unmeasured=self._unmeasured(end_sound))
        with watch(target, "The Finisher"):
            finish = self.finisher.finish(target, _fingerprint(target), facts)
        if finish is None or not finish.edits:
            return stop("ACCEPT", "Loop converged. The Finisher had nothing to finish.",
                        cycles, converged=True)
        bad = violation(target, finish, authorization)
        if bad:
            finish.status = TransformationStatus.REJECTED
            return stop("FINISH_REJECTED", f"Finishing: {bad[1]}. The finishing change was not applied; "
                        "the converged loop result stands.", cycles, converged=True, finish=finish)
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

    def _keep_test(self, target: Path, proposal: Transformation, observed: tuple[Defect, ...],
                   python: str, notes: list[str], number: int) -> tuple[str, str]:
        """"What happens if I don't delete it?" Returns ("", "") on pass, else (scope, reason): "systemic" stops the loop, "candidate" declines this one removal.

        The code is kept but made to raise when it runs. If the suite then fails,
        something executes it. Files are restored whatever happens.
        """
        if self.ghost_tools_root is None:
            return "systemic", "Ghost is not configured, so the removal cannot be validated."
        if not self.run_tests:
            return "systemic", "The suite is not being run, so the removal cannot be validated."
        if self._calibrate(python, notes) is False:
            return "systemic", "SWIZZLE's proofs do not hold."
        wanted = {d.ghost_id for d in proposal.known_defects if d.ghost_id}
        if not wanted:
            return "candidate", "The removal cites no Ghost finding to validate it against."
        if not wanted <= {d.ghost_id for d in observed if d.ghost_id}:
            return "candidate", "Ghost does not report the finding behind this removal."
        variant = keep_variant(target, proposal)
        if variant is None:
            return "candidate", "The removed code cannot be made to fail loudly, so the keep test cannot run."
        before = self._suite(target, python, notes, f"cycle {number} keep test baseline")
        if before is None or not before.green:
            return "systemic", "The suite is not green."
        snapshot = {rel: (target / rel).read_text(encoding="utf-8") for rel in variant}
        try:
            for rel, text in variant.items():
                (target / rel).write_text(text, encoding="utf-8")
            trapped = self._suite(target, python, notes, f"cycle {number} keep test (code made to fail)")
        finally:
            _restore(target, snapshot)
        if trapped is None or preserved(before, trapped) is not None:
            notes.append(f"Cycle {number}: keep test FAILED. The suite noticed when the code broke, "
                         "so something uses it.")
            return "candidate", "Keep test failed: the code is still used."
        notes.append(f"Cycle {number}: keep test passed. Nothing ran the code when it was made to fail.")
        return "", ""

    def _apply(self, target: Path, proposal: Transformation, auth: Authorization, python: str,
               notes: list[str], number: int, seen: int, validated: bool = False) -> "_Applied":
        if not validated and is_deletion(target, proposal):
            notes.append("A removal reached the applier without two loop validations. Refused.")
            return _Applied(number, seen, proposal, False, "REFUSED", None, None, {})
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
        observed = defects_from_ghost(self._scan(target, python))
        notes.append(f"Ghost Tools observed {len(observed)} finding(s).")
        return observed

    def _scan(self, target: Path, python: str):
        """Ghost's findings. Ghost reports only, so the tree must not change while it runs."""
        try:
            with watch(target, "Ghost Tools"):
                return ghost_scan(target, ghost_tools_root=self.ghost_tools_root, python=python)
        except SeatBrokeCharter:
            raise
        except Exception as err:  # noqa: BLE001 - any failure to see is UNKNOWN, not "no findings"
            raise GhostUnavailable(
                f"Ghost could not be run or read ({type(err).__name__}: {str(err)[:120]}). "
                "Observation is UNKNOWN; nothing further was attempted.") from err

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
        reobserved = defects_from_ghost(self._scan(target, python))
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


def _commented(target: Path, proposal: Transformation) -> Optional[Transformation]:
    """The same proposal, but commenting the code out instead of deleting it."""
    files = commented_variant(target, proposal, stamp_now())
    if files is None:
        return None
    proposal.edits = tuple(FileEdit(path=rel, kind="write", new=text,
                                    old=(target / rel).read_text(encoding="utf-8"))
                           for rel, text in files.items())
    proposal.intent = "comment out unused code (not deleted): " + proposal.intent
    return proposal


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


def _is_warden(target: Path) -> bool:
    """Warden's own tree, recognised by what it contains and not by what the folder is called."""
    return (target / "warden" / "authorization.py").is_file()


def _refuse_self_authorization(target: Path, authorization: Optional[Authorization]) -> None:
    """Warden may transform other repos. Transforming itself under its own
    proposal is the self-certifying loop. Checked on the contents of the target
    and on the actor, wherever the folder lives and whatever it is called."""
    if authorization and authorization.granted and authorization.actor.strip().lower() in {"warden", "self", "unknown", ""}:
        raise Unauthorized(f"{authorization.actor!r} cannot authorize a write; a human or external governor must.")
    if authorization and authorization.granted and _is_warden(target) \
            and authorization.actor.strip().lower().startswith(("warden", "drafter", "burnish", "ghost", "swizzle", "assay")):
        raise Unauthorized("Warden cannot authorize work on itself.")


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
