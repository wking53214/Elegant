"""CNS interoperability analysis.

CNS is permanently read-only. This module never writes into a CNS tree,
never vendors CNS source, and never copies gate.py.

It records a *recommendation* for another repository:

    INTERNAL_CONVERGENCE | ADAPTER | NO_ACTION | DEFER

A CNS mention in a file is not a seam. A variable named subject_digest
is not proof that subject-binding semantics match CNS.

Digest interoperability: native digest and CNS digest are recorded
separately. Equality is never assumed.

Outcome translation: PASS / RETRY / TERMINAL_BREACH are CNS semantics.
This module will not map a domain status onto them without an explicit
Translation record.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .narrative import Narrative, inspect_tree


class CnsRecommendation(str, Enum):
    INTERNAL_CONVERGENCE = "internal_convergence"
    ADAPTER = "adapter"
    NO_ACTION = "no_action"
    DEFER = "defer"


@dataclass(frozen=True)
class Translation:
    source_outcome: str
    source_semantics: str
    cns_outcome: str
    reason: str
    information_preserved: str
    information_lost: str
    authority_preserved: str
    epistemic_preserved: str
    subject_preserved: str
    provenance_preserved: str


@dataclass(frozen=True)
class CnsAnalysis:
    repository: str
    recommendation: CnsRecommendation
    reason: str
    native_representation: str
    cns_representation: str
    meaning_preserved: str
    meaning_transformed: str
    meaning_collapsed: str
    meaning_dropped: str
    subject_binding: str
    digest_model: str
    translations: tuple[Translation, ...]
    cns_modified: str  # always "NO" for this campaign


def analyse(root: Path, narrative: Narrative | None = None) -> CnsAnalysis:
    nar = narrative or inspect_tree(Path(root))
    name = Path(nar.root).name
    if name == "CNS":
        return CnsAnalysis(
            repository=name,
            recommendation=CnsRecommendation.NO_ACTION,
            reason="CNS is the contract. Elegant does not modify it. CNS CHANGE REQUIRED = DEFER / NO ACTION.",
            native_representation="cns (private contract)",
            cns_representation="self",
            meaning_preserved="n/a",
            meaning_transformed="none",
            meaning_collapsed="none",
            meaning_dropped="none",
            subject_binding="CNS owns subject_digest; this campaign does not reimplement it",
            digest_model="native CNS canonicalization; not copied here",
            translations=(),
            cns_modified="NO",
        )
    if not nar.cns_mentioned:
        return CnsAnalysis(
            repository=name,
            recommendation=CnsRecommendation.NO_ACTION,
            reason="No cns import or cns.gate/cns.graph mention in this tree. Forcing a seam would be decorative.",
            native_representation="domain-owned",
            cns_representation="none",
            meaning_preserved="n/a",
            meaning_transformed="none",
            meaning_collapsed="none",
            meaning_dropped="none",
            subject_binding="not established",
            digest_model="native digest, if any, is not assumed equal to CNS",
            translations=(),
            cns_modified="NO",
        )
    # Mentioned. Default to adapter, not internal rewrite, unless the tree
    # already imports cns as its authoritative row types.
    imports = [m.path for m in nar.modules if m.cns_import]
    rec = CnsRecommendation.ADAPTER
    reason = (
        "The tree mentions CNS. Domain machinery stays here. A boundary adapter "
        "is the default; internal convergence requires evidence that the "
        "authoritative representation already *is* a CNS row."
    )
    if name in {"composition-engine"}:
        rec = CnsRecommendation.ADAPTER
        reason = (
            "composition-engine already optional-imports cns.gate and falls back "
            "locally. Keep the adapter. Do not vendor CNS. Do not treat the "
            "fallback digest (json.dumps) as the CNS canonical digest."
        )
    return CnsAnalysis(
        repository=name,
        recommendation=rec,
        reason=reason,
        native_representation="see importing modules: " + ", ".join(imports) or "UNKNOWN",
        cns_representation="optional import of private cns, not vendored",
        meaning_preserved="UNKNOWN without reading each adapter",
        meaning_transformed="UNKNOWN",
        meaning_collapsed="UNKNOWN",
        meaning_dropped="UNKNOWN",
        subject_binding="do not treat a field named subject_digest as proof of CNS binding",
        digest_model="record native digest and CNS digest separately; never silently replace",
        translations=(),
        cns_modified="NO",
    )


def to_dict(a: CnsAnalysis) -> dict:
    return {
        "repository": a.repository,
        "recommendation": a.recommendation.value,
        "reason": a.reason,
        "native_representation": a.native_representation,
        "cns_representation": a.cns_representation,
        "meaning_preserved": a.meaning_preserved,
        "meaning_transformed": a.meaning_transformed,
        "meaning_collapsed": a.meaning_collapsed,
        "meaning_dropped": a.meaning_dropped,
        "subject_binding": a.subject_binding,
        "digest_model": a.digest_model,
        "cns_modified": a.cns_modified,
        "translations": [
            {
                "source_outcome": t.source_outcome,
                "cns_outcome": t.cns_outcome,
                "reason": t.reason,
            }
            for t in a.translations
        ],
    }
