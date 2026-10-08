"""Built-in proposers for known, evidence-backed transformations.

A proposer sees Ghost findings and the frozen ground truth. It returns a
Transformation that has not been applied. One intentional change per
proposal: documentation honesty for a false test-count claim.
"""

from __future__ import annotations

import re
from pathlib import Path

from .models import Defect, FileEdit, Transformation, TransformationStatus
from .narrative import inspect_tree
from .swizzle import GroundTruth

#: A sentence presenting a count as tests that passed: "All 16 tests passed
#: unmodified on python3." or "16 tests passed in CI." The whole sentence is
#: matched (up to its full stop or line end) so it can be replaced whole.
_CLAIM_SENTENCE = re.compile(
    r"[^.\n]*?\b(?:All\s+)?(\d+)\s+tests?\s+passed\b[^.\n]*\.?")


def _honest_sentence(match: "re.Match[str]", counted: int) -> str:
    """The replacement for one false claim: what is counted now, and what was claimed.

    It says how many test functions the tree holds, not that they passed:
    the proposer has counted them, not run them. The old number is kept, in
    a form no count-claim check reads as a current claim.
    """
    claimed = int(match.group(1))
    if claimed == counted:
        return match.group(0)
    lead = re.match(r"\s*", match.group(0)).group(0)
    return (f"{lead}The tree contains {counted} `test_*` functions "
            f"(an earlier version of this document gave {claimed}).")


def documentation_honesty_proposer(
    target: Path,
    observed: tuple[Defect, ...],
    ground: GroundTruth,
) -> Transformation:
    """If a document claims N tests and the tree has M, rewrite the claim.

    Does not split functions. Does not rename APIs. Documentation only.
    """
    target = Path(target)
    nar = inspect_tree(target)
    defects = [
        d for d in observed
        if d.file and d.file.endswith((".md",)) and "test" in d.summary.lower()
    ]
    edits: list[FileEdit] = []
    evidence = [d.identity for d in observed]

    # Rewrite the whole sentence that carries a false count, not just the
    # number inside it. Splicing a clause into the old sentence kept its tail
    # and produced text like "... (historical claim of 16 ...) unmodified on
    # the system python3." (registry run, 2026-10-07). One clean sentence is
    # the beautiful version and still keeps the historical number.
    for doc in ("PROVENANCE.md", "README.md"):
        path = target / doc
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        new = _CLAIM_SENTENCE.sub(lambda m: _honest_sentence(m, nar.test_functions), text)
        if new != text:
            edits.append(FileEdit(path=doc, kind="write", new=new, old=text))

    if not edits:
        # Propose a no-op-with-reason so the tag team can still refuse/apply
        # cleanly: documentation already honest about counts.
        return Transformation(
            target=str(target.resolve()),
            intent="no documentation-count rewrite required",
            architectural_reason="test-count claims already match the tree, or none exist",
            affected_files=(),
            expected_behavior="tree unchanged",
            preservation_requirements=("source behaviour unchanged",),
            known_defects=observed,
            transformation_scope="none",
            baseline_reference=ground.readme_sha16,
            evidence=tuple(evidence),
            edits=(),
            status=TransformationStatus.PROPOSED,
        )

    return Transformation(
        target=str(target.resolve()),
        intent="make test-count claims match the current tree without deleting historical numbers",
        architectural_reason=(
            "A provenance or README that states a test count the tree does not "
            "have is a claims-vs-reality defect. Historical counts remain labelled "
            "historical. Source is not rewritten."
        ),
        affected_files=tuple(e.path for e in edits),
        expected_behavior="Python behaviour preserved; documents distinguish history from current count",
        preservation_requirements=(
            "no .py file is edited",
            f"test_* count remains {ground.test_functions}",
        ),
        known_defects=tuple(defects) or observed,
        transformation_scope="documentation",
        baseline_reference=ground.readme_sha16,
        evidence=tuple(evidence),
        edits=tuple(edits),
        status=TransformationStatus.PROPOSED,
    )
