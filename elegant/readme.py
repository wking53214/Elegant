"""README compilation.

The README is the book of the source. It is compiled from the narrative
the code already contains, plus the critic's negative findings. It must
never claim more than the source and executed evidence establish.

This module writes a README only as part of an authorized Transformation.
It does not invent passing tests.
"""

from __future__ import annotations

from .critic import CriticReport
from .narrative import Narrative


REQUIRED_HEADINGS = (
    "WHAT THIS IS",
    "WHY IT EXISTS",
    "WHAT IT OWNS",
    "WHAT IT DOES NOT OWN",
    "ARCHITECTURAL STORY",
    "KEY INTERNAL CONCEPTS",
    "IMPORTANT BOUNDARIES",
    "LIFECYCLE / EXECUTION MODEL",
    "WHAT WORKS",
    "WHAT IS BEAUTIFUL",
    "WHAT IS IMPLEMENTED",
    "WHAT IS PROVEN",
    "WHAT IS NOT PROVEN",
    "WHAT DOES NOT WORK",
    "WHAT IS STILL UGLY",
    "KNOWN DEFECTS",
    "ARCHITECTURAL DEBT",
    "WHAT REMAINS OUTSTANDING",
    "CLAIMS VS REALITY",
)


def compile_readme(
    narrative: Narrative,
    critic: CriticReport,
    *,
    extra_sections: dict[str, str] | None = None,
    practical: str = "",
) -> str:
    extra = extra_sections or {}
    name = narrative.name
    desc = narrative.description or "(no pyproject description)"
    scripts = ", ".join(s for s, _ in narrative.scripts) or "none declared"
    modules = "\n".join(
        f"- `{m.path}` — {m.purpose or '(no module docstring)'}"
        for m in narrative.modules
        if not m.path.startswith("tests/") and "Tests/" not in m.path
    ) or "- (no Python modules)"

    beautiful = "\n".join(f"- {x}" for x in critic.what_is_beautiful) or "- (none recorded in this inspection)"
    ugly = "\n".join(f"- {x}" for x in critic.what_is_ugly) or "- (none recorded in this inspection)"
    unfinished = "\n".join(f"- {x}" for x in critic.what_is_unfinished) or "- (none recorded)"
    claims = "\n".join(
        f"- `{c.text}` — {c.note} [{c.epistemic.value}]"
        for c in critic.claims
    ) or "- No numeric claims were extracted."

    proven = (
        f"- This inspection counted **{narrative.test_functions}** `test_*` functions "
        f"in {len(narrative.test_files)} file(s). Counting is not execution."
    )
    not_proven = (
        "- A green count of test *names* is not a passing suite.\n"
        "- Elegant does not claim this README is complete.\n"
        f"- Critic verdict: {critic.verdict}"
    )

    body = f"""# {name}

> {desc}

## WHAT THIS IS

{extra.get("WHAT THIS IS", f"`{name}` as declared by its own tree. Version `{narrative.version or "UNKNOWN"}`.")}

## WHY IT EXISTS

{extra.get("WHY IT EXISTS", "See the module docstrings. If they do not say, that absence is the answer.")}

## WHAT IT OWNS

{extra.get("WHAT IT OWNS", "- Whatever its modules declare. Modules that never say so are listed as unfinished.")}

## WHAT IT DOES NOT OWN

{extra.get("WHAT IT DOES NOT OWN", "- Whatever this README does not have evidence for. Absence of a denial is not a grant.")}

## ARCHITECTURAL STORY

{modules}

Console scripts: {scripts}

## KEY INTERNAL CONCEPTS

{extra.get("KEY INTERNAL CONCEPTS", "- See class names in the modules above.")}

## IMPORTANT BOUNDARIES

{extra.get("IMPORTANT BOUNDARIES", "- Elegant does not infer a runtime path from a directory name.")}

## LIFECYCLE / EXECUTION MODEL

{extra.get("LIFECYCLE / EXECUTION MODEL", "- UNKNOWN unless a module docstring states it.")}

## WHAT WORKS

{extra.get("WHAT WORKS", "- UNKNOWN until a test is executed in this campaign and cited.")}

## WHAT IS BEAUTIFUL

{beautiful}

## WHAT IS IMPLEMENTED

- Python modules in this tree: {len(narrative.modules)}
- `test_*` functions counted: {narrative.test_functions}

## WHAT IS PROVEN

{proven}

## WHAT IS NOT PROVEN

{not_proven}

## WHAT DOES NOT WORK

{extra.get("WHAT DOES NOT WORK", "- UNKNOWN. Failures not executed here are not listed as passing.")}

## WHAT IS STILL UGLY

{ugly}

## KNOWN DEFECTS

{extra.get("KNOWN DEFECTS", ugly)}

## ARCHITECTURAL DEBT

{extra.get("ARCHITECTURAL DEBT", unfinished)}

## WHAT REMAINS OUTSTANDING

{unfinished}

## CLAIMS VS REALITY

Here is what the artifact says it is.

Here is what we can actually establish that it is.

Here is where those two disagree.

{claims}

Critic: **{critic.verdict}**

{practical}
"""
    return body
