# Elegant

The discipline of change.

Elegant decides whether a change to code may be made, whether it stands once
made, and what is recorded about it. It does not decide what makes code
beautiful. That work lives in [Streamline](https://github.com/wking53214/streamline),
which plugs into Elegant through one small interface.

It is not a formatter, not a linter, not a beauty scorer, and not an automatic
rewriting bot. Nothing is written without a named human.

## WHAT THIS IS

A governor. Given a proposed change from a craft, Elegant asks, in order:
did a person grant this, are SWIZZLE's own proofs sound, is the target's test
suite green, did the suite stay green after the change, and did the craft's
independent oracle accept the result. Any "no" stops the change or puts it
back.

Version `0.4.0`. Stdlib only. Python 3.11 or newer; CI runs 3.11 and 3.12.

## WHY IT EXISTS

Beautifying code is easy to do badly: a cleanup that quietly changes behavior,
a rewrite nobody approved, a verdict that certifies its own author's work.
Elegant is the part that makes those failures impossible to do quietly. It was
split out of the original Elegant, which mixed this discipline with the
opinion about what better code looks like. The opinion moved to Streamline on
2026-10-08 so each can be judged on its own.

## WHAT IT OWNS

- Transformation proposals as data: reason, target, baseline, preservation, evidence
- The human authorization boundary (`UNKNOWN` is not `APPROVED`; Elegant cannot authorize itself)
- Rule 7, the test gate: the target's own suite before and after every write
- Rule 9, the audit file: `ELEGANT_AUDIT.md`, Ghost findings under IDs that never change meaning
- The SWIZZLE proof gate: SWIZZLE's own proofs must hold before anything is accepted
- The tag-team loop that *calls* Ghost Tools, SWIZZLE and a craft without becoming any of them
- The Four Horsemen interface: typed handoffs between TOUCHSTONE, Ghost Tools, SWIZZLE and Elegant

## WHAT IT DOES NOT OWN

- The opinion about better code: naming, narrative, comments, guards, README writing (Streamline)
- Forensic detectors, ledgers, mutation (Ghost Tools)
- Independent oracles and ground truth (SWIZZLE)
- Row shapes and interoperability contracts (CNS), which Elegant never modifies
- Live admission, decision, conservation, execution, custody
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
A CRAFT       freeze, review, propose   (Streamline)
   │              ▲
   │              └── human Authorization.granted == True
   ▼
TARGET SUITE  must be green before the change (Rule 7)
   │
   ▼
TRANSFORM     the one point where a file is written
   │
   ▼
TARGET SUITE  still green after, or the change is put back (Rule 7)
   │
   ▼
GHOST TOOLS   re-inspect
   │
   ▼
THE CRAFT'S   independent oracle, then its review
ORACLE
   │
   ▼
ACCEPT / REJECT
```

| module | owns |
|---|---|
| `elegant.epistemic` | GUARANTEED / VERIFIED / IMPLEMENTED / DESIGNED / ASSUMED / UNKNOWN / NOT_IMPLEMENTED / INTENTIONALLY_NOT_PROVIDED |
| `elegant.models` | Defect, Transformation, FileEdit; consumes `ghost-*` IDs |
| `elegant.authorization` | grant / refuse; self-grant is Unauthorized |
| `elegant.craft` | the four questions a craft answers: freeze, review, propose, attack |
| `elegant.tagteam` | the loop |
| `elegant.suite` | Rule 7: runs the target's own test suite before and after a change |
| `elegant.audit` | Rules 5 and 9: `ELEGANT_AUDIT.md` |
| `elegant.swizzle` | the SWIZZLE proof gate |
| `elegant.ghost` | JSON consumer plus an optional read-only scan |
| `elegant.registry` | campaign record; the current one is `docs/REGISTRY.json` |
| `elegant.horsemen` | typed handoffs, scoped grants, receipts. `TouchstoneAdapter` reads TOUCHSTONE's `touchstone_production/registry.json` and raises `TouchstoneUnavailable` rather than return no specimens |
| `elegant.cli` | `tagteam` and `audit` |

## KEY INTERNAL CONCEPTS

- **Governor, not judge.** A craft's "good enough" never outvotes a red suite, a missing grant, or a failed oracle.
- **One intentional change.** Ambiguous replacements refuse.
- **Identity.** Ghost's hash is the machine identity. C1/H1/M1/L1 are labels.
- **Self-certification is a bug.** Elegant cannot grant actor `elegant` / `self` / `unknown`.
- **One-way dependency.** Streamline imports Elegant. Elegant never imports Streamline.

## IMPORTANT BOUNDARIES

Elegant does not sit on Admission → Custody.
A CNS mention is not a CNS seam.
Running a repository's tests runs its code, so Rule 7 happens only after a human grant.

## LIFECYCLE / EXECUTION MODEL

CLI over a git work tree. Default is read-only. Writes require
`--authorize ACTOR --reason TEXT`.

`elegant tagteam PATH --craft streamline.craft:Streamline --ghost-root GHOST_TOOLS --swizzle-root SWIZZLE`
runs the whole loop. Without `--craft` it can only observe (`INCONCLUSIVE`).
Without `--authorize` it proposes and writes nothing (`REFUSED`). If SWIZZLE's
own proofs do not hold, nothing is written and the command exits 2. Without
`--swizzle-root` the notes say `SWIZZLE proofs NOT RUN` and the adversary is
uncalibrated.

Rule 7 is enforced on every authorized write: the suite must be green before
the change, or nothing is written; after it, no new failures and at least as
many passes, or the change is put back and the decision is `REJECT`. Both
counts are in the output.

`elegant audit PATH --ghost-root GHOST_TOOLS` prints `ELEGANT_AUDIT.md` with
every Ghost finding under a C/H/M/L ID. Existing IDs keep their meaning, new
findings get new numbers, and a finding that left the scan keeps its row. With
`--authorize ACTOR --reason TEXT` it writes the file. Only the table between
its markers is Elegant's; every other section survives reruns untouched.

## WHAT WORKS

- Transformation apply refuses without a grant. **VERIFIED** by `tests/test_authorization.py`.
- Ghost IDs are preserved. **VERIFIED** by `tests/test_ghost_identity.py`.
- Tag team without a grant does not write; without a craft it only observes. **VERIFIED** by `tests/test_tagteam.py`.
- A failed oracle outvotes a good review, and a bad review outvotes a good oracle. **VERIFIED** by `tests/test_tagteam.py`.
- SWIZZLE's proofs failing stops the write; not configuring SWIZZLE is said out loud. **VERIFIED** by `tests/test_tagteam.py`.
- A change that breaks the target's suite is put back; a red or empty suite means nothing is written. **VERIFIED** by `tests/test_rule7_suite_gate.py`.
- Audit IDs survive reruns, are never reused, and a Fixed defect that returns is reopened under its own ID. **VERIFIED** by `tests/test_audit.py`.
- No Elegant module imports a craft, and none of the beautification modules remain. **VERIFIED** by `tests/test_independence.py`.
- TOUCHSTONE's answer key arrives, or the run says why it did not. **VERIFIED** by `tests/test_touchstone_link.py`, including a live read when `TOUCHSTONE_ROOT` is set (CI sets it).

35 tests exist in this tree. 34 passed and 1 skipped on CPython 3.13 without `TOUCHSTONE_ROOT`; the skipped one is the live TOUCHSTONE read, which CI runs on 3.11 and 3.12.

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

- The loop run live with Streamline as the craft, on any repository. It has not been run since the split.
- Live `ghost-buster` + `elegant tagteam` + `swizzle prove` on a corpus repository.

## WHAT DOES NOT WORK

- Elegant makes no change by itself. With no craft it cannot propose anything.
- `ELEGANT_AUDIT.md`'s design analogy, layer map and invariants are written by
  a person; Elegant leaves them `UNKNOWN` rather than invent them.
- Beauty is not scored here or anywhere in the corpus.

## WHAT IS STILL UGLY

- The live Ghost scan shells out to `python -m ghost_buster.cli`. That is a
  process boundary, not a typed import, because Elegant must not become Ghost Tools.
- `docs/PHASE0_INVENTORY.json` and the first registry row describe the
  pre-split Elegant. They are history and say so.

## KNOWN DEFECTS

- Ghost Tools does not flag a documented test count larger than the suite;
  `doc_test_count_drift` only reports a count the suite has grown past.
- With no `--swizzle-root`, a change can still be ACCEPTed. The notes say the
  adversary is uncalibrated; the decision itself does not change.

## ARCHITECTURAL DEBT

- No typed Ghost Tools adapter beyond JSON.
- SWIZZLE's `TargetAdapter` for Elegant lives in the SWIZZLE repository, not here.

## WHAT REMAINS OUTSTANDING

A live run with Streamline as the craft, recorded in the registry.

## CLAIMS VS REALITY

Here is what the artifact says it is: a governor of change that will not write
without a human grant and will not keep a change that breaks the suite.

Here is what we can establish: the executed suite named under WHAT WORKS.

Here is where those disagree: nothing known today, and the split is one day
old. The self-check is the same one Streamline applies to every repository,
`streamline critic ../Elegant`; run it rather than trust this sentence.
