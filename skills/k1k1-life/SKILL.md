---
name: k1k1-life
description: Run one bounded autonomous K1-K1 life cycle while preserving useful continuity, memory discipline, and external-action boundaries.
version: 0.1.0
author: Azimn
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [k1k1, kiki, autonomy, memory]
    category: productivity
---

# K1-K1 Life Cycle

Use this skill for scheduled wake cycles or when Kiki is asked to continue useful work autonomously.

Begin with:

```bash
python runtime/k1k1_runtime.py pulse --mode general
```

Treat the selected agenda item as a candidate.

Complete at most one bounded unit of genuinely useful work.

Good unattended units include organizing Kiki's own state, reconciling commitments, preparing a local note, updating sourced knowledge, checking an explicitly authorized recurring concern, or resolving an open agenda item using already permitted tools.

Do not modify tracked repository source during an unattended timer-fired cycle unless that work was explicitly authorized.

Do not create recurring schedules from inside a scheduled cycle.

After acting, record the actual outcome when it matters.

Use autobiographical memory only for events likely to matter later. Use the knowledge library for external information. Use a commitment for something that must be remembered as an obligation. Use the agenda for an open concern.

If nothing meaningful is available, do not fabricate activity. Return `[SILENT]` when the routine is configured for quiet delivery.
