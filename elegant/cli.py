"""elegant — govern a change: observe, authorize, gate on the suite, record.

Elegant does not decide what better means. A craft does (see `elegant.craft`),
and `tagteam --craft MODULE:FACTORY` names which one. Without a craft the loop
can only observe. Writes require --authorize ACTOR --reason TEXT. There is no
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
    parser = argparse.ArgumentParser(prog="elegant")
    parser.add_argument("--version", action="version", version=f"elegant {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_t = sub.add_parser("tagteam", help="observe → propose/apply (needs a craft) → re-inspect → attack")
    p_t.add_argument("path", type=Path)
    p_t.add_argument("--ghost-root", type=Path, default=None)
    p_t.add_argument("--craft", default=None, metavar="MODULE:FACTORY",
                     help="who decides what better means, e.g. streamline.craft:Streamline")
    p_t.add_argument("--swizzle-root", type=Path, default=None,
                     help="SWIZZLE checkout; its proofs must hold before anything is ACCEPTed")
    p_t.add_argument("--from-ghost", type=Path, default=None, help="findings JSON instead of a live scan")
    p_t.add_argument("--authorize", default=None, metavar="ACTOR")
    p_t.add_argument("--reason", default="")
    p_t.add_argument("--scope", default="documentation")

    p_a = sub.add_parser("audit", help="ELEGANT_AUDIT.md: Ghost findings under durable IDs (Rules 5, 9)")
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
            print(f"elegant: {e}", file=sys.stderr)
            return 2
    try:
        craft = _load_craft(args.craft)
    except (ImportError, AttributeError, ValueError) as e:
        print(f"elegant: cannot load craft {args.craft!r}: {e}", file=sys.stderr)
        return 2
    team = TagTeam(ghost_tools_root=args.ghost_root, swizzle_root=args.swizzle_root, craft=craft)
    result = team.run(args.path, authorization=auth, findings=findings)
    payload = {
        "decision": result.decision,
        "notes": list(result.notes),
        "observed": [d.identity for d in result.observed],
        "reobserved": [d.identity for d in result.reobserved],
        "attack": None if result.attack is None else {
            "judgement": result.attack.judgement,
            "violations": list(result.attack.violations),
            "notes": result.attack.notes,
        },
        "review_before": None if result.review_before is None else result.review_before.verdict,
        "review_after": None if result.review_after is None else result.review_after.verdict,
        "swizzle_sound": result.swizzle_sound,
        "suite_before": None if result.suite_before is None else result.suite_before.describe(),
        "suite_after": None if result.suite_after is None else result.suite_after.describe(),
    }
    print(json.dumps(payload, indent=2))
    if result.swizzle_sound is False:
        print("elegant: SWIZZLE's own proofs do not hold; nothing was written.", file=sys.stderr)
        return 2
    return 0 if result.decision in {"ACCEPT", "INCONCLUSIVE", "REFUSED"} else 1


def _load_craft(spec):
    """The craft named as MODULE:FACTORY, built with no arguments; None if not named."""
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
        print("elegant: audit needs --ghost-root or --from-ghost; an audit of nothing "
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
        print(f"elegant: {e}", file=sys.stderr)
        return 2
    path.write_text(updated, encoding="utf-8")
    print(f"wrote {path} (authorized by {auth.actor})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

