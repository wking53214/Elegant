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

Version `0.1.0`. Stdlib only. Python ≥ 3.11 declared; the suite in this campaign
was executed on CPython 3.10.21 because that is what the sandbox had with
pytest. That interpreter difference is recorded, not papered over.

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
| `elegant.registry` | campaign record |

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

## WHAT WORKS

- Transformation apply refuses without a grant. **VERIFIED** by `tests/test_authorization.py` (executed this campaign).
- Ghost IDs are preserved. **VERIFIED** by `tests/test_ghost_identity.py`.
- A README that claims 16 tests when the tree has 2 is not good enough. **VERIFIED** by `tests/test_critic.py`.
- Tag team without auth does not write. **VERIFIED** by `tests/test_tagteam.py`.
- Documentation-honesty oracle does not import the critic. **VERIFIED** by `tests/test_swizzle_independence.py`.
- CNS analysis of an unrelated tree writes nothing and recommends `no_action`. **VERIFIED** by `tests/test_cns_readonly.py`.

Executed this campaign: **15 passed** (`python3 -m pytest -q` in this repository, CPython 3.10.21).

## WHAT IS BEAUTIFUL

The refusal is in the type of the work, not in a comment: `apply` checks
`authorization.granted` before a path is opened.

## WHAT IS IMPLEMENTED

The modules in the table above. CLI commands listed. No network. No I/O in
CNS analysis beyond reading the target tree.

## WHAT IS PROVEN

The 15 tests named above, on one interpreter, this run. That is not a proof
of the whole architecture, of Ghost Tools integration in production CI, or
of SWIZZLE's own catalogue.

## WHAT IS NOT PROVEN

- Live `ghost-buster` + `elegant tagteam` + `swizzle prove` on every corpus repo
- That a README rewrite preserves every reader-visible contract
- That CPython 3.11/3.12 CI has run (the workflow file is **IMPLEMENTED**, not **VERIFIED** here)
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

None filed against this tree at first publication. The poetry critic, pointed
at Elegant itself after this README is written, is the next inspection — not
this paragraph claiming the inspection already happened.

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

Here is what we can establish: 15 executed tests, on one interpreter, covering
that refusal, identity preservation, critic honesty, tag-team refusal-to-write,
oracle independence, and CNS non-modification of an unrelated tree.

Here is where those disagree: the README describes a corpus campaign; this
package is the *instrument*. The campaign's GitHub SHAs, live Ghost scans, and
SWIZZLE attacks are evidence *outside* this repository and must be recorded
in the registry, not implied by this file.

Critic (self, after this README exists): run `elegant critic .` rather than
trust this sentence.
