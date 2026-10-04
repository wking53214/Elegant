"""elegant — inspect, criticise, propose, apply, tag-team.

Writes require --authorize ACTOR --reason TEXT. There is no default actor.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .authorization import Unauthorized, grant
from .cns_boundary import analyse as cns_analyse, to_dict as cns_to_dict
from .critic import PoetryCritic
from .ghost import defects_from_file, load_findings
from .narrative import inspect_tree
from .readme import compile_readme
from .tagteam import TagTeam


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="elegant")
    parser.add_argument("--version", action="version", version=f"elegant {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ins = sub.add_parser("inspect", help="extract the architectural narrative")
    p_ins.add_argument("path", type=Path)

    p_c = sub.add_parser("critic", help="poetry critic: claims vs the tree")
    p_c.add_argument("path", type=Path)

    p_t = sub.add_parser("tagteam", help="observe → (optional) propose/apply → re-inspect → attack")
    p_t.add_argument("path", type=Path)
    p_t.add_argument("--ghost-root", type=Path, default=None)
    p_t.add_argument("--from-ghost", type=Path, default=None, help="findings JSON instead of a live scan")
    p_t.add_argument("--authorize", default=None, metavar="ACTOR")
    p_t.add_argument("--reason", default="")
    p_t.add_argument("--scope", default="documentation")

    p_cns = sub.add_parser("cns", help="CNS interoperability recommendation (never modifies CNS)")
    p_cns.add_argument("path", type=Path)

    args = parser.parse_args(argv)
    if args.command == "inspect":
        nar = inspect_tree(args.path)
        print(json.dumps({
            "name": nar.name,
            "version": nar.version,
            "test_functions": nar.test_functions,
            "test_files": list(nar.test_files),
            "cns_mentioned": nar.cns_mentioned,
            "readme_exists": nar.readme_exists,
            "modules": [
                {"path": m.path, "purpose": m.purpose, "classes": list(m.classes)}
                for m in nar.modules
            ],
        }, indent=2))
        return 0
    if args.command == "critic":
        report = PoetryCritic().critique(args.path)
        print(report.as_markdown())
        return 0 if report.good_enough else 1
    if args.command == "cns":
        print(json.dumps(cns_to_dict(cns_analyse(args.path)), indent=2))
        return 0
    if args.command == "tagteam":
        findings = list(load_findings(args.from_ghost)) if args.from_ghost else None
        auth = None
        if args.authorize:
            try:
                auth = grant(
                    args.authorize,
                    "transform",
                    str(Path(args.path).resolve()),
                    args.scope,
                    args.reason,
                )
            except Unauthorized as e:
                print(f"elegant: {e}", file=sys.stderr)
                return 2
        team = TagTeam(ghost_tools_root=args.ghost_root)
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
            "critic_before": result.critic_before.verdict,
            "critic_after": None if result.critic_after is None else result.critic_after.verdict,
        }
        print(json.dumps(payload, indent=2))
        return 0 if result.decision in {"ACCEPT", "INCONCLUSIVE", "REFUSED"} else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
