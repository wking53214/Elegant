# Stack role — Elegant

**ASSURANCE (not the live decision path).**

The governor of code change. Decides whether a change may be made and whether
it stands: a human grant, a green suite before and after, SWIZZLE's proofs,
a durable record. Never silently rewrites; never certifies itself. Which fix to
propose is the Proposer's job; beautifying and the final README are Streamline's.

| Related | Role |
|---------|------|
| [ghost_tools](https://github.com/wking53214/ghost_tools) | Forensic observation. Owns findings, baselines, ledgers. |
| [SWIZZLE](https://github.com/wking53214/SWIZZLE) | Adversarial challenge. Owns independent oracles and ground truth. Its proofs must hold before Elegant ACCEPTs. |
| Proposer (github.com/wking53214/Proposer) | In the loop. Proposes one fix at a time as data; never writes. Plugs into Elegant through `elegant.roles`. |
| [Streamline](https://github.com/wking53214/streamline) | The finisher. Runs once, after the loop converges: beautifies the code and writes the final README with the critic's commentary. Plugs into Elegant through `elegant.roles`. Imports Elegant; Elegant never imports it. |
| [TOUCHSTONE](https://github.com/wking53214/TOUCHSTONE) | Specimen answer key, read from `touchstone_production/registry.json`. |
| CNS (private) | Interoperability contracts. Elegant may analyse a seam. Elegant never modifies CNS. |

```text
Live path: Admission → OBSERVE/Keys → Locks → PERCEIVE → Decision → Conservation → Execution → Custody
Assurance: ghost_tools · Elegant · SWIZZLE · TOUCHSTONE
```

```text
CODEBASE
   │
   ▼
┌─ LOOP (repeat until converged) ──────────────┐
│ GHOST TOOLS  reports what is wrong           │
│ PROPOSER     proposes one fix                │
│ ELEGANT      authorize / gate / apply        │
│ GHOST TOOLS  re-inspect                      │
│ SWIZZLE      calibrated and checked          │
└──────────────────────────────────────────────┘
   │ converged
   ▼
STREAMLINE   once: beautify + final README + critic's commentary
   │          (applied by Elegant under the same gate)
   ▼
ACCEPT / FINISH_REJECTED
```

Elegant does not replace Ghost Tools. Elegant does not replace SWIZZLE.
Elegant does not become a CNS dumping ground.

See [README.md](README.md).
