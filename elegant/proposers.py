"""Built-in proposers for known, evidence-backed transformations.

A proposer sees Ghost findings and the frozen ground truth. It returns a
Transformation that has not been applied. One intentional change per
proposal: documentation honesty for a false test-count claim.
"""

from __future__ import annotations

from pathlib import Path

from .models import Defect, FileEdit, Transformation, TransformationStatus
from .narrative import inspect_tree
from .swizzle import GroundTruth


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

    # Always correct PROVENANCE-style "All N tests passed" when N != count.
    for doc in ("PROVENANCE.md", "README.md"):
        path = target / doc
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        new = text
        import re
        def repl(m: re.Match[str]) -> str:
            n = int(m.group(1))
            if n == nar.test_functions:
                return m.group(0)
            return (
                f"{nar.test_functions} `test_*` functions are present in the "
                f"current tree (historical claim of {n} is preserved as history, "
                f"not as current count)"
            )
        new = re.sub(
            r"All (\d+) tests passed",
            repl,
            new,
        )
        new = re.sub(
            r"(\d+) tests? passed unmodified",
            repl,
            new,
        )
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
