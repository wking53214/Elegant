"""warden — govern a change: observe, authorize, gate on the suite, record.

Warden does not decide what a good fix or good code looks like. A Drafter
(in the loop) and a Finisher (once, after it) do; see `warden.roles`.
`tagteam --drafter MODULE:FACTORY --finisher MODULE:FACTORY` names them.
Without a drafter the loop can only observe. Writes require --authorize ACTOR --reason TEXT. There is no
default actor.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

from . import __version__
from .authorization import Unauthorized, grant
from . import audit as audit_file
from .ghost import load_findings, scan as ghost_scan
from .tagteam import TagTeam


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="warden")
    parser.add_argument("--version", action="version", version=f"warden {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_t = sub.add_parser("tagteam", help="loop: observe → propose → apply → re-inspect, until converged; then finish once")
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
        return _tagteam(args)
    return 2


def _tagteam(args) -> int:
    """Run the loop once and print what happened as JSON."""
    findings = list(load_findings(args.from_ghost)) if args.from_ghost else None
    auth = None
    if args.authorize:
        try:
            auth = grant(args.authorize, "transform", str(Path(args.path).resolve()),
                         args.scope, args.reason)
        except Unauthorized as e:
            print(f"warden: {e}", file=sys.stderr)
            return 2
    try:
        drafter = _load_seat(args.drafter)
        finisher = _load_seat(args.finisher)
        judge = _load_seat(args.judge)
    except (ImportError, AttributeError, ValueError) as e:
        print(f"warden: cannot load seat: {e}", file=sys.stderr)
        return 2
    team = TagTeam(ghost_tools_root=args.ghost_root, swizzle_root=args.swizzle_root,
                   assay_root=args.assay_root, assay_floor=args.assay_floor,
                   drafter=drafter, finisher=finisher, judge=judge, max_cycles=args.max_cycles)
    result = team.run(args.path, authorization=auth, findings=findings)
    payload = {
        "decision": result.decision,
        "converged": result.converged,
        "cycles": [{"number": c.number, "outcome": c.outcome, "observed": c.observed}
                   for c in result.cycles],
        "finished": result.finished,
        "notes": list(result.notes),
        "observed": [d.identity for d in result.observed],
        "reobserved": [d.identity for d in result.reobserved],
        "swizzle_sound": result.swizzle_sound,
        "unmeasured": list(result.unmeasured),
        "verdict": None if result.verdict is None else {
            "decision": result.verdict.decision, "reasons": list(result.verdict.reasons),
            "judge": result.verdict.judge},
    }
    print(json.dumps(payload, indent=2))
    if result.swizzle_sound is False:
        print("warden: SWIZZLE's own proofs do not hold; nothing was written.", file=sys.stderr)
        return 2
    return {"ACCEPT": 0, "INCONCLUSIVE": 0, "REFUSED": 0, "ACCEPT_UNVERIFIED": 3}.get(result.decision, 1)


def _load_seat(spec):
    """The seat-filler named as MODULE:FACTORY, built with no arguments; None if not named."""
    if not spec:
        return None
    module_name, _, attr = spec.partition(":")
    if not module_name or not attr:
        raise ValueError("expected MODULE:FACTORY")
    return getattr(importlib.import_module(module_name), attr)()


def _audit(args) -> int:
    """Print the updated audit; write it only under a human grant."""
    root = Path(args.path).resolve()
    if args.from_ghost:
        findings = load_findings(args.from_ghost)
    elif args.ghost_root:
        findings = ghost_scan(root, ghost_tools_root=args.ghost_root)
    else:
        print("warden: audit needs --ghost-root or --from-ghost; an audit of nothing "
              "would read as a clean repository", file=sys.stderr)
        return 2
    path = root / audit_file.FILENAME
    current = path.read_text(encoding="utf-8") if path.is_file() else ""
    updated = audit_file.update(current, findings)
    if not args.authorize:
        print(updated)
        return 0
    try:
        auth = grant(args.authorize, "audit", str(root), "documentation", args.reason)
    except Unauthorized as e:
        print(f"warden: {e}", file=sys.stderr)
        return 2
    path.write_text(updated, encoding="utf-8")
    print(f"wrote {path} (authorized by {auth.actor})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

