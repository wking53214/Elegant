# Warden

The discipline of change.

Warden decides whether a change to code may be made, whether it stands once
made, and what is recorded about it. It does not decide what makes code
beautiful. That work lives in [Burnish](https://github.com/wking53214/burnish),
which plugs into Warden through one small interface.

It is not a formatter, not a linter, not a beauty scorer, and not an automatic
rewriting bot. Nothing is written without a named human.

## WHAT THIS IS

A governor, and the only thing in the stack that writes. It runs a loop. Ghost
Tools reports what is wrong, the Drafter proposes one fix, and Warden asks, in
order: did a person grant this, are SWIZZLE's own proofs sound, is the target's
test suite green, did it stay green after the change, and does Ghost agree
nothing new appeared. Any "no" stops the change or puts it back. The loop
cycles until the Drafter has nothing left to propose (or a cycle limit is
hit). Only then does Warden hand the code, once, to the Finisher, together with the facts it measured (the suite result and what Ghost still reports), so the Finisher counts and detects nothing itself. The Finisher beautifies the code and writes the final README. The Finisher's change goes through
the same gate.

Version `0.6.0`. Stdlib only. Python 3.11 or newer; CI runs 3.11 and 3.12.

## WHY IT EXISTS

Beautifying code is easy to do badly: a cleanup that quietly changes behavior,
a rewrite nobody approved, a verdict that certifies its own author's work.
Warden is the part that makes those failures impossible to do quietly. It was
split out of the original Warden, which mixed this discipline with the
opinion about what better code looks like. The opinion moved to Burnish on
2026-10-08 so each can be judged on its own.

## WHAT IT OWNS

- Transformation proposals as data: reason, target, baseline, preservation, evidence
- The human authorization boundary (`UNKNOWN` is not `APPROVED`; Warden cannot authorize itself)
- Rule 7, the test gate: the target's own suite before and after every write
- Rule 9, the audit file: `WARDEN_AUDIT.md`, Ghost findings under IDs that never change meaning
- The SWIZZLE proof gate: SWIZZLE's own proofs must hold before anything is accepted
- The tag-team loop that *calls* Ghost Tools, SWIZZLE, a Drafter and a Finisher without becoming any of them
- The Four Horsemen interface: typed handoffs between ASSAY, Ghost Tools, SWIZZLE and Warden

## WHAT IT DOES NOT OWN

- Which fix to propose (Drafter), and the beautifying and final README (Burnish)
- Forensic detectors, ledgers, mutation (Ghost Tools)
- Independent oracles and ground truth (SWIZZLE)
- Row shapes and interoperability contracts (CNS), which Warden never modifies
- Live admission, decision, conservation, execution, custody
- A numeric elegance score

## ARCHITECTURAL STORY

```
CODEBASE
   │
   ▼
SWIZZLE       proves its own instrument first; nothing is written if its proofs fail
   │
   ▼
┌─ THE LOOP, repeated until the Drafter has nothing left ───────────────┐
│  GHOST TOOLS   observe / find   (findings keep ghost-* identity)       │
│  DRAFTER      proposes one change (data, never a write)               │
│  human grant   Authorization.granted == True                           │
│  TARGET SUITE  green before (Rule 7)                                   │
│  WARDEN       applies the change: the one point a file is written     │
│  TARGET SUITE  green after, or the change is put back                  │
│  GHOST TOOLS   re-inspect                                              │
└─────────────────────────────────────────────────────────────────────────┘
   │  converged (or NOT_CONVERGED at the cycle limit: no hand-off)
   ▼
SWIZZLE       proofs checked again
   │
   ▼
FINISHER      once: beautified code and the final README (Burnish)
   │          Warden applies it under the same gate; the suite breaking or
   │          any new Ghost finding puts it back
   ▼
ACCEPT / FINISH_REJECTED
```

| module | owns |
|---|---|
| `warden.epistemic` | GUARANTEED / VERIFIED / IMPLEMENTED / DESIGNED / ASSUMED / UNKNOWN / NOT_IMPLEMENTED / INTENTIONALLY_NOT_PROVIDED |
| `warden.models` | Defect, Transformation, FileEdit; consumes `ghost-*` IDs |
| `warden.authorization` | grant / refuse; self-grant is Unauthorized |
| `warden.roles` | the two seats: Drafter (in the loop) and Finisher (once, after it) |
| `warden.tagteam` | the loop |
| `warden.suite` | Rule 7: runs the target's own test suite before and after a change |
| `warden.audit` | Rules 5 and 9: `WARDEN_AUDIT.md` |
| `warden.swizzle` | the SWIZZLE proof gate |
| `warden.ghost` | JSON consumer plus an optional read-only scan |
| `warden.registry` | campaign record; the current one is `docs/REGISTRY.json` |
| `warden.horsemen` | typed handoffs, scoped grants, receipts. `AssayAdapter` reads ASSAY's `assay_production/registry.json` and raises `AssayUnavailable` rather than return no specimens |
| `warden.cli` | `tagteam` and `audit` |

## KEY INTERNAL CONCEPTS

- **Governor, not judge.** A Drafter or Finisher never outvotes a red suite, a missing grant, or a new Ghost finding.
- **Converged is not clean.** The loop ends when the Drafter has nothing left, not when Ghost reports zero; the notes say how many findings remain.
- **One intentional change.** Ambiguous replacements refuse.
- **Identity.** Ghost's hash is the machine identity. C1/H1/M1/L1 are labels.
- **Self-certification is a bug.** Warden cannot grant actor `warden` / `self` / `unknown`.
- **One-way dependency.** Drafter and Burnish import Warden's data shapes. Warden imports neither.

## IMPORTANT BOUNDARIES

Warden does not sit on Admission → Custody.
A CNS mention is not a CNS seam.
Running a repository's tests runs its code, so Rule 7 happens only after a human grant.

## LIFECYCLE / EXECUTION MODEL

CLI over a git work tree. Default is read-only. Writes require
`--authorize ACTOR --reason TEXT`.

`warden tagteam PATH --drafter MODULE:FACTORY --finisher MODULE:FACTORY --ghost-root GHOST_TOOLS --swizzle-root SWIZZLE`
runs the whole loop and the hand-off (`--max-cycles`, default 10). Without
`--drafter` it can only observe (`INCONCLUSIVE`). Without `--finisher` it stops
when the loop converges.
Without `--authorize` it proposes and writes nothing (`REFUSED`). If SWIZZLE's
own proofs do not hold, nothing is written and the command exits 2. Without
`--swizzle-root` the notes say `SWIZZLE proofs NOT RUN` and the adversary is
uncalibrated.

Rule 7 is enforced on every authorized write: the suite must be green before
the change, or nothing is written; after it, no new failures and at least as
many passes, or the change is put back and the decision is `REJECT`. Both
counts are in the output.

`warden audit PATH --ghost-root GHOST_TOOLS` prints `WARDEN_AUDIT.md` with
every Ghost finding under a C/H/M/L ID. Existing IDs keep their meaning, new
findings get new numbers, and a finding that left the scan keeps its row. With
`--authorize ACTOR --reason TEXT` it writes the file. Only the table between
its markers is Warden's; every other section survives reruns untouched.

## WHAT WORKS

- Transformation apply refuses without a grant. **VERIFIED** by `tests/test_authorization.py`.
- Ghost IDs are preserved. **VERIFIED** by `tests/test_ghost_identity.py`.
- Tag team without a grant does not write; without a drafter it only observes. **VERIFIED** by `tests/test_tagteam.py`.
- The loop cycles until the drafter runs dry, stops at the cycle limit, and notices a drafter going in circles. **VERIFIED** by `tests/test_tagteam.py`.
- The finisher runs once, only after convergence, and a finishing change that breaks the suite is put back while the loop's result stands. **VERIFIED** by `tests/test_tagteam.py`.
- SWIZZLE's proofs failing stops the write; not configuring SWIZZLE is said out loud. **VERIFIED** by `tests/test_tagteam.py`.
- A change that breaks the target's suite is put back; a red or empty suite means nothing is written. **VERIFIED** by `tests/test_rule7_suite_gate.py`.
- Audit IDs survive reruns, are never reused, and a Fixed defect that returns is reopened under its own ID. **VERIFIED** by `tests/test_audit.py`.
- No Warden module imports Burnish, Drafter or any other repository in the stack, and none of the beautification modules remain. **VERIFIED** by `tests/test_independence.py`.
- ASSAY's answer key arrives, or the run says why it did not. **VERIFIED** by `tests/test_assay_link.py`, including a live read when `ASSAY_ROOT` is set (CI sets it).

38 tests exist in this tree. 37 passed and 1 skipped on CPython 3.13 without `ASSAY_ROOT`; the skipped one is the live ASSAY read, which CI runs on 3.11 and 3.12.

## WHAT IS BEAUTIFUL

The refusal is in the type of the work, not in a comment: `apply` checks
`authorization.granted` before a path is opened.

## WHAT IS IMPLEMENTED

The modules in the table above and the two CLI commands. No network.

## WHAT IS PROVEN

The tests named above. The whole loop, live, once on 2026-10-07 (before the
split): SWIZZLE 12 of 12 proofs, Ghost Tools observe and re-inspect, an
authorized change, oracle ACCEPT, on a scratch demo. Recorded in
`docs/REGISTRY.json`. That is not a proof of the architecture.

## WHAT IS NOT PROVEN

- The loop run live with a real Drafter and Finisher, on any repository. It has not been run since the split.
- Live `ghost-buster` + `warden tagteam` + `swizzle prove` on a corpus repository.

## WHAT DOES NOT WORK

- Warden makes no change by itself. With no drafter it cannot propose anything.
- `WARDEN_AUDIT.md`'s design analogy, layer map and invariants are written by
  a person; Warden leaves them `UNKNOWN` rather than invent them.
- Beauty is not scored here or anywhere in the corpus.

## WHAT IS STILL UGLY

- The live Ghost scan shells out to `python -m ghost_buster.cli`. That is a
  process boundary, not a typed import, because Warden must not become Ghost Tools.
- `docs/PHASE0_INVENTORY.json` and the first registry row describe the
  pre-split Warden. They are history and say so.

## KNOWN DEFECTS

- Ghost Tools does not flag a documented test count larger than the suite;
  `doc_test_count_drift` only reports a count the suite has grown past.
- With no `--swizzle-root`, a change can still be ACCEPTed. The notes say the
  adversary is uncalibrated; the decision itself does not change.

## ARCHITECTURAL DEBT

- No typed Ghost Tools adapter beyond JSON.
- SWIZZLE's `TargetAdapter` for Warden lives in the SWIZZLE repository, not here.

## WHAT REMAINS OUTSTANDING

A live run with Drafter and Burnish in their seats, recorded in the registry.

## CLAIMS VS REALITY

Here is what the artifact says it is: a governor of change that will not write
without a human grant and will not keep a change that breaks the suite.

Here is what we can establish: the executed suite named under WHAT WORKS.

Here is where those disagree: nothing known today, and the split is one day
old. The self-check is the same one Burnish applies to every repository,
`burnish critic ../Warden`; run it rather than trust this sentence.
