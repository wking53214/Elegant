"""warden — govern a change: observe, authorize, gate on the suite, record.

Warden does not decide what a good fix or good code looks like. A Drafter
(in the loop) and a Finisher (once, after it) do; see `warden.roles`.
`tagteam --drafter MODULE:FACTORY --finisher MODULE:FACTORY` names them.
Without a drafter the loop can only observe. Writes require --authorize ACTOR --reason TEXT. There is no
default actor.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
import json
import sys
from pathlib import Path

from . import CONTRACT, __version__
from .authorization import Unauthorized, grant
from . import audit as audit_file, textio, versions
from .ghost import load_report, scan as ghost_scan
from .tagteam import TagTeam


#: What `warden tagteam` exits with, by decision. Anything not listed here exits 1, never 0.
EXIT_CODES = {
    "ACCEPT": 0,
    "REJECT": 1,
    "JUDGE_REJECTED": 1,
    "NOT_CONVERGED": 1,
    "FINISH_REJECTED": 1,
    "USAGE_ERROR": 2,
    "SEAT_NOT_LOADED": 2,
    "ACCEPT_UNVERIFIED": 3,
    "ERROR": 4,
    "REFUSED": 5,
    "INCONCLUSIVE": 6,
}

EXIT_CODE_HELP = """\
exit codes (only 0 means the change was accepted):
  0  ACCEPT. Measured, judged, and standing.
  1  REJECT, JUDGE_REJECTED, NOT_CONVERGED, FINISH_REJECTED, or any other rejection.
  2  usage error, a seat could not be loaded, or SWIZZLE's own proofs are unsound. Nothing was written.
  3  ACCEPT_UNVERIFIED. Changes stand but a check did not run or the Judge could not decide.
  4  ERROR. A seat failed or gave the wrong kind of answer. Nothing was approved.
  5  REFUSED. No human authorization. A proposal was shown; nothing was written.
  6  INCONCLUSIVE. A needed measurement could not be made (Ghost down, a red suite from the
     start, an unusable ASSAY key). Nothing was written.
The command always prints valid JSON on stdout; `reason` says why in one sentence."""


class ContractMismatch(ValueError):
    """A seat was written for a different version of Warden's shapes."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="warden")
    parser.add_argument("--version", action="version", version=f"warden {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_t = sub.add_parser("tagteam", help="loop: observe → propose → apply → re-inspect, until converged; then finish once",
                         epilog=EXIT_CODE_HELP, formatter_class=argparse.RawDescriptionHelpFormatter)
    p_t.add_argument("path", type=Path)
    p_t.add_argument("--ghost-root", type=Path, default=None)
    p_t.add_argument("--drafter", default=None, metavar="MODULE:FACTORY",
                     help="in the loop: proposes fixes, e.g. drafter.seat:Drafter")
    p_t.add_argument("--judge", default=None, metavar="MODULE:FACTORY",
                     help="at the end, once: reads the evidence and decides ACCEPT or REJECT. "
                          "Without one, a run cannot be ACCEPTed, only ACCEPT_UNVERIFIED")
    p_t.add_argument("--finisher", default=None, metavar="MODULE:FACTORY",
                     help="after the loop, once: beautifies and writes the final README")
    p_t.add_argument("--max-cycles", type=int, default=10)
    p_t.add_argument("--ghost-timeout", type=float, default=600,
                     help="seconds one Ghost scan may take; longer counts as Ghost being down (default 600)")
    p_t.add_argument("--swizzle-root", type=Path, default=None,
                     help="SWIZZLE checkout; its proofs must hold before anything is ACCEPTed")
    p_t.add_argument("--assay-root", type=Path, default=None,
                     help="ASSAY checkout; with --swizzle-root, Ghost is graded against its answer key first")
    p_t.add_argument("--assay-floor", type=int, default=3,
                     help="the fewest known failure modes Ghost must catch for the Judge to accept "
                          "(default 3, where Ghost stands today; 0 records the score without enforcing it)")
    p_t.add_argument("--from-ghost", type=Path, default=None, help="findings JSON instead of a live scan")
    p_t.add_argument("--authorize", default=None, metavar="ACTOR")
    p_t.add_argument("--reason", default="")
    p_t.add_argument("--scope", default="documentation",
                     help="documentation: prose files only. code: anything outside tests, test config and CI")

    p_a = sub.add_parser("audit", help="WARDEN_AUDIT.md: Ghost findings under durable IDs (Rules 5, 9)")
    p_a.add_argument("path", type=Path)
    p_a.add_argument("--ghost-root", type=Path, default=None)
    p_a.add_argument("--from-ghost", type=Path, default=None, help="findings JSON instead of a live scan")
    p_a.add_argument("--authorize", default=None, metavar="ACTOR",
                     help="write the file; without it the result is printed and nothing is written")
    p_a.add_argument("--reason", default="")

    args = parser.parse_args(argv)
    if args.command == "audit":
        return _audit(args)
    if args.command == "tagteam":
        try:
            return _tagteam(args)
        except Unauthorized as e:
            return _stop("REFUSED", str(e))
        except Exception as e:  # noqa: BLE001 - the CLI always prints valid JSON, never a traceback
            return _stop("ERROR", f"Warden failed with {type(e).__name__}. Nothing was approved.")
    return 2


def _print_json(payload) -> None:
    print(json.dumps(payload, indent=2))


def _stop(decision: str, reason: str, notes: list[str] | None = None) -> int:
    """End before a run: valid JSON on stdout, the reason on stderr, and the exit code for `decision`."""
    _print_json({"decision": decision, "reason": reason, "contract": CONTRACT, "notes": (notes or []) + [reason]})
    print(f"warden: {reason}", file=sys.stderr)
    return EXIT_CODES[decision]


def _tagteam(args) -> int:
    """Run the loop once and print what happened as JSON."""
    path = Path(args.path)
    if not path.is_dir():
        what = "does not exist" if not path.exists() else "is not a directory"
        return _stop("USAGE_ERROR", f"The target {str(path)!r} {what}. Nothing was run.")
    findings = load_report(args.from_ghost) if args.from_ghost else None
    auth = None
    if args.authorize:
        if not args.reason.strip():
            return _stop("REFUSED", "a reason is required")
        try:
            auth = grant(args.authorize, "transform", str(path.resolve()), args.scope, args.reason)
        except Unauthorized as e:
            return _stop("REFUSED", str(e))
    warnings: list[str] = []
    try:
        with contextlib.redirect_stdout(sys.stderr):
            drafter = _load_seat(args.drafter, warnings)
            finisher = _load_seat(args.finisher, warnings)
            judge = _load_seat(args.judge, warnings)
    except ContractMismatch as e:
        return _stop("SEAT_NOT_LOADED", str(e))
    except Exception as e:  # noqa: BLE001 - a seat that will not load is named, never a traceback
        return _stop("SEAT_NOT_LOADED", f"A seat could not be loaded ({type(e).__name__}: {str(e)[:120]}).")
    for w in warnings:
        print(f"warden: warning: {w}", file=sys.stderr)
    return _run_team(args, auth, findings, drafter, finisher, judge, warnings)


def _run_team(args, auth, findings, drafter, finisher, judge, warnings=()) -> int:
    team = TagTeam(ghost_tools_root=args.ghost_root, swizzle_root=args.swizzle_root,
                   assay_root=args.assay_root, assay_floor=args.assay_floor,
                   drafter=drafter, finisher=finisher, judge=judge, max_cycles=args.max_cycles,
                   ghost_timeout=args.ghost_timeout)
    # A seat that print()s must not corrupt the JSON on stdout.
    with contextlib.redirect_stdout(sys.stderr):
        result = team.run(args.path, authorization=auth, findings=findings)
    payload = {
        "decision": result.decision,
        "converged": result.converged,
        "cycles": [{"number": c.number, "outcome": c.outcome, "observed": c.observed}
                   for c in result.cycles],
        "finished": result.finished,
        "put_back": result.put_back,
        "reason": None if result.decision == "ACCEPT" else (result.reason or (result.notes[-1] if result.notes else "")),
        "notes": list(result.notes) + list(warnings),
        "observed": [d.identity for d in result.observed],
        "reobserved": [d.identity for d in result.reobserved],
        "contract": CONTRACT,
        "versions": _versions(args, drafter, finisher, judge),
        "swizzle_sound": result.swizzle_sound,
        "unmeasured": list(result.unmeasured),
        "ghost_scan": result.ghost_scan,
        "drafter_skipped": list(result.drafter_skipped),
        "verdict": None if result.verdict is None else {
            "decision": result.verdict.decision, "reasons": list(result.verdict.reasons),
            "judge": result.verdict.judge},
    }
    _print_json(payload)
    if result.swizzle_sound is False:
        print("warden: SWIZZLE's own proofs do not hold; nothing was written.", file=sys.stderr)
        return 2
    return EXIT_CODES.get(result.decision, 1)


def _versions(args, drafter, finisher, judge) -> dict:
    """What took part in this run: Warden, the instrument checkouts given, and the seats loaded."""
    import warden
    return versions.report(
        warden_module=warden, contract=CONTRACT, version=__version__,
        ghost_root=args.ghost_root, swizzle_root=args.swizzle_root, assay_root=args.assay_root,
        seats={"drafter": versions.seat(args.drafter, drafter),
               "finisher": versions.seat(args.finisher, finisher),
               "judge": versions.seat(args.judge, judge)})


def _load_seat(spec, warnings: list[str] | None = None):  # `warnings` is kept for old callers; unused now
    """The seat-filler named as MODULE:FACTORY, built with no arguments; None if not named.

    A seat must declare `requires_contract`, the version of Warden's shapes it was written for. A
    different version is refused, and so is a seat that declares nothing: Warden cannot know such
    a seat fits, and it will not govern a run with a part it has not checked.
    """
    if not spec:
        return None
    module_name, _, attr = spec.partition(":")
    if not module_name or not attr:
        raise ValueError("expected MODULE:FACTORY")
    seat = getattr(importlib.import_module(module_name), attr)()
    wanted = getattr(seat, "requires_contract", None)
    if wanted is None:
        raise ContractMismatch(f"The seat {spec} does not say which Warden contract it was written for, so its fit "
                               f"with this Warden (contract {CONTRACT!r}) cannot be checked. Nothing was run. "
                               f'Add requires_contract = "{CONTRACT}" to the seat.')
    if not isinstance(wanted, str) or wanted != CONTRACT:
        raise ContractMismatch(f"The seat {spec} was written for Warden contract {wanted!r} but this Warden "
                               f"is contract {CONTRACT!r}. Nothing was run.")
    return seat


def _audit(args) -> int:
    """Print the updated audit; write it only under a human grant."""
    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"warden: the target {str(args.path)!r} does not exist or is not a directory.", file=sys.stderr)
        return 2
    try:
        if args.from_ghost:
            findings = load_report(args.from_ghost)
        elif args.ghost_root:
            findings = ghost_scan(root, ghost_tools_root=args.ghost_root)
        else:
            findings = None
    except Exception as e:  # noqa: BLE001 - an audit that could not read its findings must not look clean
        print(f"warden: the findings could not be read ({type(e).__name__}: {str(e)[:120]}). "
              "Nothing was printed or written.", file=sys.stderr)
        return 2
    if findings is not None and getattr(findings, "blind", None):
        print(f"warden: {findings.blind}. Nothing was printed or written.", file=sys.stderr)
        return 2
    if getattr(findings, "gaps", None):
        print("warden: warning: Ghost's scan had gaps (" + "; ".join(findings.gaps[:3]) + "), so a row marked "
              "'not seen in latest scan' may only be one Ghost could not look at.", file=sys.stderr)
    if findings is None:
        print("warden: audit needs --ghost-root or --from-ghost; an audit of nothing "
              "would read as a clean repository", file=sys.stderr)
        return 2
    path = root / audit_file.FILENAME
    if path.is_symlink() or not path.resolve().is_relative_to(root):
        print(f"warden: {path} is a link or points outside the target; the audit will not be read "
              "or written through it.", file=sys.stderr)
        return 2
    try:
        current = textio.read_text(path) if path.is_file() else ""
    except textio.Undecodable:
        print(f"warden: {path} is not valid UTF-8, so it will not be touched.", file=sys.stderr)
        return 2
    try:
        updated = audit_file.update(current, findings)
    except Exception as e:  # noqa: BLE001 - garbled findings must not produce a half-made audit
        print(f"warden: the findings could not be used ({type(e).__name__}). Nothing was printed or written.",
              file=sys.stderr)
        return 2
    if not args.authorize:
        print(updated)
        return 0
    if current.strip() and not audit_file.has_markers(current):
        print(f"warden: {path} exists, has no Warden markers ({audit_file.BEGIN} and {audit_file.END}), "
              "and looks hand-written. It was not changed. Add the two markers where the table should go, "
              "or move the file aside.", file=sys.stderr)
        return 2
    try:
        auth = grant(args.authorize, "audit", str(root), "documentation", args.reason)
    except Unauthorized as e:
        print(f"warden: {e}", file=sys.stderr)
        return 2
    try:
        textio.write_text(path, updated)
    except OSError as e:
        print(f"warden: {path} could not be written ({type(e).__name__}).", file=sys.stderr)
        return 2
    print(f"wrote {path} (authorized by {auth.actor})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

