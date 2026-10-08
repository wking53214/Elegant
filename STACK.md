# Stack role — Warden

**ASSURANCE (not the live decision path).**

The governor of code change. Decides whether a change may be made and whether
it stands: a human grant, a green suite before and after, SWIZZLE's proofs,
a durable record. Never silently rewrites; never certifies itself. Which fix to
propose is the Drafter's job; beautifying and the final README are Burnish's.

| Related | Role |
|---------|------|
| [ghost_tools](https://github.com/wking53214/ghost_tools) | Forensic observation. Owns findings, baselines, ledgers. |
| [SWIZZLE](https://github.com/wking53214/SWIZZLE) | Adversarial challenge. Owns independent oracles and ground truth. Its proofs must hold before Warden ACCEPTs. |
| Drafter (github.com/wking53214/Drafter) | In the loop. Proposes one fix at a time as data; never writes. Plugs into Warden through `warden.roles`. |
| [Burnish](https://github.com/wking53214/burnish) | The finisher. Runs once, after the loop converges: beautifies the code and writes the final README with the critic's commentary. Plugs into Warden through `warden.roles`. Imports Warden; Warden never imports it. |
| [ASSAY](https://github.com/wking53214/ASSAY) | Specimen answer key, read from `assay_production/registry.json`. |
| CNS (private) | Interoperability contracts. Warden may analyse a seam. Warden never modifies CNS. |

```text
Live path: Admission → OBSERVE/Keys → Locks → PERCEIVE → Decision → Conservation → Execution → Custody
Assurance: ghost_tools · Warden · SWIZZLE · ASSAY
```

```text
CODEBASE
   │
   ▼
┌─ LOOP (repeat until converged) ──────────────┐
│ GHOST TOOLS  reports what is wrong           │
│ DRAFTER     proposes one fix                │
│ WARDEN      authorize / gate / apply        │
│ GHOST TOOLS  re-inspect                      │
│ SWIZZLE      calibrated and checked          │
└──────────────────────────────────────────────┘
   │ converged
   ▼
BURNISH   once: beautify + final README + critic's commentary
   │          (applied by Warden under the same gate)
   ▼
ACCEPT / FINISH_REJECTED
```

Warden does not replace Ghost Tools. Warden does not replace SWIZZLE.
Warden does not become a CNS dumping ground.

See [README.md](README.md).
