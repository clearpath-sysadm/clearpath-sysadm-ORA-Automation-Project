---
name: Prefer reversible removal
description: Project-level rule for deleting operational and historical business records.
---

Use auditable archive/restore behavior instead of hard deletion for inventory and other business records. Preserve original identities and historical references. Keep permanent purge outside routine application workflows unless an exceptional purge requirement is explicitly approved.

**Why:** The user explicitly stated that accidental deletion must be reversible and that soft deletes should generally replace hard deletes. Historical inventory and shipment traceability must not be destroyed by routine UI actions.

**How to apply:** When adding or changing removal flows, distinguish operational states from archive state, record actor/reason/time, exclude archives from operational queries, preserve references, and provide controlled restore behavior.