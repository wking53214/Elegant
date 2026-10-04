# Stack role — Elegant

**ASSURANCE (not the live decision path).**

Software-writing and architectural-transparency system. Consumes forensic
evidence; proposes source and README transformations; never silently
rewrites; never certifies itself.

| Related | Role |
|---------|------|
| [ghost_tools](https://github.com/wking53214/ghost_tools) | Forensic observation. Owns findings, baselines, ledgers. |
| [SWIZZLE](https://github.com/wking53214/SWIZZLE) | Adversarial challenge. Owns independent oracles and ground truth. |
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
ELEGANT      propose / transform (human-authorized)
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
