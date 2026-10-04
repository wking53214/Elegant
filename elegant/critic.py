"""The poetry critic.

Its job is not to praise the code. It is allowed — required — to say:

    This isn't good enough yet.

It does not produce a beauty score. It compares claims in the README and
module prose against what the tree actually contains, and against what
has actually been counted in this process (test function names, files,
declared scripts).

A README is allowed to contain negative findings. That is a feature.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .epistemic import EpistemicState
from .narrative import Narrative, inspect_tree


@dataclass(frozen=True)
class Claim:
    text: str
    location: str
    epistemic: EpistemicState
    supported: bool
    note: str


@dataclass(frozen=True)
class CriticReport:
    target: str
    good_enough: bool
    verdict: str
    claims: tuple[Claim, ...]
    what_is_beautiful: tuple[str, ...]
    what_is_ugly: tuple[str, ...]
    what_is_unfinished: tuple[str, ...]
    unsupported: tuple[str, ...]
    unknown: tuple[str, ...]

    def as_markdown(self) -> str:
        lines = [
            f"# Poetry critic — {self.target}",
            "",
            self.verdict,
            "",
            "## Claims vs reality",
        ]
        for c in self.claims:
            mark = "supported" if c.supported else "UNSUPPORTED"
            lines.append(f"- ({c.epistemic.value}, {mark}) {c.text} — {c.note}")
        lines += ["", "## What is beautiful"]
        lines += [f"- {x}" for x in self.what_is_beautiful] or ["- (nothing recorded)"]
        lines += ["", "## What is still ugly"]
        lines += [f"- {x}" for x in self.what_is_ugly] or ["- (nothing recorded)"]
        lines += ["", "## What is unfinished"]
        lines += [f"- {x}" for x in self.what_is_unfinished] or ["- (nothing recorded)"]
        if self.unsupported:
            lines += ["", "## Unsupported"]
            lines += [f"- {x}" for x in self.unsupported]
        if self.unknown:
            lines += ["", "## UNKNOWN"]
            lines += [f"- {x}" for x in self.unknown]
        return "\n".join(lines) + "\n"


class PoetryCritic:
    """Brutally honest. No scores."""

    def critique(self, root: Path, narrative: Narrative | None = None) -> CriticReport:
        nar = narrative or inspect_tree(Path(root))
        claims: list[Claim] = []
        ugly: list[str] = []
        beautiful: list[str] = []
        unfinished: list[str] = []
        unsupported: list[str] = []
        unknown: list[str] = []

        if not nar.readme_exists:
            ugly.append("There is no README. The book of the source is missing.")
            unfinished.append("README")
        else:
            if _has_honest_sections(nar.readme_text):
                beautiful.append("The README already distinguishes ownership, non-goals, and honest status.")
            if _sounds_like_marketing(nar.readme_text) and not _has_honest_sections(nar.readme_text):
                ugly.append("The README reads as a product brochure. It does not say what is still ugly.")
                unsupported.append("polished README without a claims-vs-reality section")

        for phrase, n in nar.test_count_claims():
            supported = n == nar.test_functions
            note = (
                f"tree currently contains {nar.test_functions} test_* functions"
            )
            claims.append(
                Claim(
                    text=phrase,
                    location="README/PROVENANCE",
                    epistemic=EpistemicState.VERIFIED if supported else EpistemicState.IMPLEMENTED,
                    supported=supported,
                    note=note if supported else f"UNSUPPORTED: {note}",
                )
            )
            if not supported:
                ugly.append(
                    f"A document claims {n} tests; this inspection counted {nar.test_functions} test_* functions."
                )
                unsupported.append(phrase)

        # Historical-as-current: living-product language plus archive markers elsewhere.
        living = bool(re.search(r"\bpip install\b", nar.readme_text)) and bool(
            re.search(r"\bUsage\b", nar.readme_text)
        )
        archived = bool(re.search(r"\b(ARCHIVED|Retired|superseded|historical reconstruction)\b", nar.readme_text, re.I))
        if living and not archived and _github_archive_hint(nar):
            ugly.append(
                "The README teaches installation and usage as if this were the "
                "current home of the design, without saying it is historical."
            )
            unsupported.append("living-product README on a superseded artifact")

        if not nar.owns:
            unfinished.append("No module states WHAT IT OWNS in the first screen of prose.")
        else:
            beautiful.append("At least one module states ownership in its own voice.")

        if nar.cns_mentioned:
            claims.append(
                Claim(
                    text="CNS is referenced",
                    location="tree",
                    epistemic=EpistemicState.IMPLEMENTED,
                    supported=True,
                    note="A CNS mention is not proof of a correct seam. Subject binding is UNKNOWN until inspected.",
                )
            )
            unknown.append("Whether any CNS digest here is the CNS canonical digest.")

        parse_failures = [m.path for m in nar.modules if m.purpose == "(unparseable)"]
        for p in parse_failures:
            ugly.append(f"{p} could not be parsed. Structural detectors cannot speak for it.")
            unfinished.append(p)

        if nar.unknowns:
            unknown.extend(nar.unknowns)

        good_enough = not unsupported and not parse_failures
        if good_enough:
            verdict = (
                "The artifact's story is consistent with what this inspection could count. "
                "That is not a proof of the whole architecture."
            )
        else:
            verdict = "This isn't good enough yet."

        return CriticReport(
            target=nar.name,
            good_enough=good_enough,
            verdict=verdict,
            claims=tuple(claims),
            what_is_beautiful=tuple(beautiful),
            what_is_ugly=tuple(ugly),
            what_is_unfinished=tuple(unfinished),
            unsupported=tuple(unsupported),
            unknown=tuple(unknown),
        )


def _has_honest_sections(text: str) -> bool:
    keys = ("WHAT IT DOES NOT", "What It Does NOT", "Brutally Honest", "CLAIMS VS REALITY", "What is still ugly")
    return sum(1 for k in keys if k in text) >= 2


def _sounds_like_marketing(text: str) -> bool:
    return bool(re.search(r"\b(powerful|seamless|state-of-the-art|simply works)\b", text, re.I)) or (
        "pip install" in text and "does NOT" not in text and "does not" not in text.lower()
    )


def _github_archive_hint(nar: Narrative) -> bool:
    """Local signal that the tree itself already knows it is historical.

    We do not fetch GitHub. PROVENANCE.md or ARCHITECTURE.md mentioning
    retirement / vendoring is enough.
    """
    root = Path(nar.root)
    for name in ("PROVENANCE.md", "ARCHITECTURE.md", "STACK.md"):
        p = root / name
        if p.is_file():
            t = p.read_text(encoding="utf-8", errors="replace")
            if re.search(r"retired|vendored|superseded|archived", t, re.I):
                return True
    return False
