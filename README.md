# Elegant

A software-writing and architectural-transparency system.

It is not a formatter, not a linter, not a beauty scorer, not an LLM style
scorer, and not an automatic rewriting bot.

«Make software so intentionally structured and so truthfully documented that
another programmer can understand the architecture by reading the artifact
itself, rather than reverse-engineering the architecture from execution paths.»

## WHAT THIS IS

Elegant owns the *story the source tells* and the *proposal to make that story
true*. Ghost Tools owns forensic observation. SWIZZLE owns adversarial
challenge. CNS owns interoperability contracts and is never modified here.

Version `0.2.0`. Stdlib only. Python ≥ 3.11 declared. The first campaign ran
the suite on CPython 3.10.21 because that is what its sandbox had; since
2026-10-07 it also runs on CPython 3.13 locally and on 3.11 and 3.12 in CI.

## WHY IT EXISTS

The corpus already had an assurance scanner and an assurance adversary. It did
not have a component whose job is: *given what is actually here, make it
intelligible without lying.* Documentation generators that praise the code
were the failure mode.

## WHAT IT OWNS

- Transformation representation (reason, target, baseline, preservation, evidence)
- Human authorization boundary (`UNKNOWN` is not `APPROVED`; Elegant cannot authorize itself)
- Poetry critic (no beauty score; allowed to say «This isn't good enough yet.»)
- README compilation from source narrative
- Tag-team orchestration that *calls* Ghost Tools and SWIZZLE
- CNS interoperability *analysis* (recommendation only)

## WHAT IT DOES NOT OWN

- Forensic detectors, ledgers, surgeons, mutation (Ghost Tools)
- Independent oracles, genomes, holdouts, minimization (SWIZZLE)
- Row shapes, gate precedence, subject_digest canonicalization (CNS)
- Live admission, decision, conservation, execution, custody
- Silent code edits
- A numeric elegance score

## ARCHITECTURAL STORY

```
CODEBASE
   │
   ▼
GHOST TOOLS   observe / find     (findings keep ghost-* identity)
   │
   ▼
SWIZZLE       swizzle prove: its own proofs must hold, or nothing is written
   │
   ▼
ELEGANT       propose / transform
   │              ▲
   │              └── human Authorization.granted == True
   ▼
GHOST TOOLS   re-inspect
   │
   ▼
SWIZZLE-style independent oracle (does not import the critic)
   │
   ▼
ACCEPT / REJECT
```

| module | owns |
|---|---|
| `elegant.epistemic` | GUARANTEED / VERIFIED / IMPLEMENTED / DESIGNED / ASSUMED / UNKNOWN / NOT_IMPLEMENTED / INTENTIONALLY_NOT_PROVIDED |
| `elegant.models` | Defect, Transformation, FileEdit; consumes `ghost-*` IDs |
| `elegant.authorization` | grant / refuse; self-grant is Unauthorized |
| `elegant.narrative` | what the tree declares |
| `elegant.critic` | claims vs the tree |
| `elegant.ghost` | JSON consumer + optional read-only scan |
| `elegant.swizzle` | freeze ground truth; documentation-honesty oracle |
| `elegant.tagteam` | the loop |
| `elegant.cns_boundary` | recommendation; `cns_modified` is always `NO` |
| `elegant.proposers` | documentation-honesty proposer |
| `elegant.cli` | `inspect` `critic` `tagteam` `cns` |
| `elegant.registry` | campaign record; the current one is `docs/REGISTRY.json` |
| `elegant.horsemen` | Four Horsemen interface (v0.2.0): typed handoffs between TOUCHSTONE, Ghost Tools, SWIZZLE and Elegant, scoped grants, receipts. `TouchstoneAdapter` reads TOUCHSTONE's `touchstone_production/registry.json` and raises `TouchstoneUnavailable` rather than return no specimens |

## KEY INTERNAL CONCEPTS

- **Museum test.** Read the source; understand the architecture. Execution still judges whether the story is true.
- **One intentional change.** Ambiguous replacements refuse.
- **Identity.** Ghost's hash is the machine identity. C1/H1/M1/L1 are labels.
- **Self-certification is a bug.** Elegant cannot grant actor `elegant` / `self` / `unknown`.

## IMPORTANT BOUNDARIES

Elegant does not sit on Admission → Custody.
A CNS mention is not a CNS seam.
A field named `subject_digest` is not proof of CNS binding.
Native digest ≠ CNS digest unless canonicalization is shown.

## LIFECYCLE / EXECUTION MODEL

CLI over a git work tree. Default is read-only. Writes require
`--authorize ACTOR --reason TEXT`.

`elegant tagteam PATH --ghost-root GHOST_TOOLS --swizzle-root SWIZZLE` runs the
whole loop. The documentation-honesty proposer is wired in, so without
`--authorize` it proposes and writes nothing (`REFUSED`); with it, the change
is applied, re-inspected and attacked. If SWIZZLE's own proofs do not hold,
nothing is written and the command exits 2. Without `--swizzle-root` the notes
say `SWIZZLE proofs NOT RUN` and the adversary is uncalibrated.

## WHAT WORKS

- Transformation apply refuses without a grant. **VERIFIED** by `tests/test_authorization.py` (executed this campaign).
- Ghost IDs are preserved. **VERIFIED** by `tests/test_ghost_identity.py`.
- A README whose test count disagrees with the tree is not good enough. **VERIFIED** by `tests/test_critic.py`.
- Tag team without auth does not write. **VERIFIED** by `tests/test_tagteam.py`.
- Documentation-honesty oracle does not import the critic. **VERIFIED** by `tests/test_swizzle_independence.py`.
- CNS analysis of an unrelated tree writes nothing and recommends `no_action`. **VERIFIED** by `tests/test_cns_readonly.py`.

- TOUCHSTONE's answer key arrives, or the run says why it did not: no root, missing, empty or broken registry all raise. **VERIFIED** by `tests/test_touchstone_link.py`, including a live read of TOUCHSTONE when `TOUCHSTONE_ROOT` is set (CI sets it).
- SWIZZLE's proofs failing stops the write and blocks ACCEPT; not configuring SWIZZLE is said out loud. **VERIFIED** by `tests/test_tagteam.py`.
- The whole loop, live, once (2026-10-07): SWIZZLE 12 of 12 proofs, Ghost Tools observe and re-inspect, an authorized documentation-honesty change, oracle ACCEPT. On a scratch demo, not a corpus repository; recorded in `docs/REGISTRY.json`.

24 tests exist in this tree. All 24 passed on CPython 3.13 with `TOUCHSTONE_ROOT` set; without it the live TOUCHSTONE test skips and says why. CI (3.11, 3.12) runs all 24.

## WHAT IS BEAUTIFUL

The refusal is in the type of the work, not in a comment: `apply` checks
`authorization.granted` before a path is opened.

## WHAT IS IMPLEMENTED

The modules in the table above. CLI commands listed. No network. No I/O in
CNS analysis beyond reading the target tree.

## WHAT IS PROVEN

The tests named above, on three interpreters, and one live run of the loop on
a scratch repository. That is not a proof of the whole architecture, of
Ghost Tools integration in production CI, or of SWIZZLE's own catalogue.

## WHAT IS NOT PROVEN

- Live `ghost-buster` + `elegant tagteam` + `swizzle prove` on any corpus repo. It has run once, on a scratch demo
- That a README rewrite preserves every reader-visible contract
- Transfer of the museum test to repositories Elegant has not transformed

## WHAT DOES NOT WORK

- There is no automatic source refactorer for long functions. That is
  **INTENTIONALLY NOT PROVIDED** in v0.1.0: the first proposer is
  documentation honesty.
- Beauty is not scored. Asking for a score is asking for the wrong tool.

## WHAT IS STILL UGLY

- Tag-team live scan still shells out to `python -m ghost_buster.cli`. That is
  a process boundary, not a typed import, because Elegant must not become
  Ghost Tools.
- README compilation produces a complete heading set even when many sections
  are UNKNOWN. Verbose UNKNOWN is honest and not elegant yet.
- This repository was empty at baseline. The architecture is new, not extracted.

## KNOWN DEFECTS

- The critic reads test counts only in two shapes ("N tests passed / exist /
  in this", "claims N test"). "**15 passed**" and "The 15 tests named above"
  stood in this README for a week after the suite grew past them, and the
  critic flagged an illustrative example sentence instead. Found 2026-10-07 by
  running `elegant critic .` on this repository.
- The documentation-honesty proposer rewrites the number and keeps the rest of
  the sentence, so the result can read badly ("... unmodified on the system
  python3" after a new clause). Seen in the registry run.
- Ghost Tools does not flag a documented count larger than the suite:
  `doc_test_count_drift` only reports a count the suite has grown past. In the
  registry run the critic found the false claim and Ghost Tools did not.

## ARCHITECTURAL DEBT

- No typed Ghost Tools adapter in *this* package beyond JSON.
- SWIZZLE `TargetAdapter` for Elegant lives in the SWIZZLE repository when
  that integration is applied, not here. Duplicating it here would be the
  self-certifying loop.

## WHAT REMAINS OUTSTANDING

Corpus-scale transformations. CNS adapters in consuming repos. A critic that
understands more than test counts and archival language.

## CLAIMS VS REALITY

Here is what the artifact says it is: an architectural-transparency system
that will not write without a human grant.

Here is what we can establish: the executed suite (see WHAT WORKS) covering
that refusal, identity preservation, critic honesty, tag-team refusal-to-write,
oracle independence, CNS non-modification of an unrelated tree, the loud
TOUCHSTONE link and the SWIZZLE proof gate; plus one live run of the whole
loop on a scratch repository.

Here is where those disagree: the README describes a corpus campaign; this
package is the *instrument*. The campaign's GitHub SHAs, live Ghost scans, and
SWIZZLE attacks are evidence *outside* this repository and must be recorded
in the registry (`docs/REGISTRY.json`), not implied by this file. As of
2026-10-07 the registry holds one row, the scratch run, and no corpus
repository.

Critic (self): `elegant critic .` on 2026-10-07, after this revision: "The
artifact's story is consistent with what this inspection could count." Before
it, the same command said "This isn't good enough yet." Run it again rather
than trust this sentence.
