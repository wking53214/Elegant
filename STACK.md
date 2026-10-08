# Stack role — Elegant

**ASSURANCE (not the live decision path).**

The governor of code change. Decides whether a change may be made and whether
it stands: a human grant, a green suite before and after, SWIZZLE's proofs,
a durable record. Never silently rewrites; never certifies itself. What counts
as better code is Streamline's job, not Elegant's.

| Related | Role |
|---------|------|
| [ghost_tools](https://github.com/wking53214/ghost_tools) | Forensic observation. Owns findings, baselines, ledgers. |
| [SWIZZLE](https://github.com/wking53214/SWIZZLE) | Adversarial challenge. Owns independent oracles and ground truth. Its proofs must hold before Elegant ACCEPTs. |
| [Streamline](https://github.com/wking53214/streamline) | The craft. Knows what better code is; plugs into Elegant through `elegant.craft`. Imports Elegant; Elegant never imports it. |
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
GHOST TOOLS  observe / find
   │
   ▼
STREAMLINE   propose (what better means)
   │
   ▼
ELEGANT      authorize / gate on the suite / transform
   │
   ▼
GHOST TOOLS  re-inspect
   │
   ▼
SWIZZLE      attack
   │
   ▼
ACCEPT / REJECT
```

Elegant does not replace Ghost Tools. Elegant does not replace SWIZZLE.
Elegant does not become a CNS dumping ground.

See [README.md](README.md).
