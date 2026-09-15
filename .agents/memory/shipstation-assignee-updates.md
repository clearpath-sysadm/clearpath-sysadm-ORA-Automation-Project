---
name: ShipStation assignee updates
description: Safety rules for copying user assignments between related ShipStation orders.
---

Use ShipStation's assignment-only endpoint rather than rewriting a full order payload. Re-fetch the target immediately before assignment and stop if it is no longer awaiting shipment or already has an assignee. Do not automatically retry an assignment POST after a timeout; its outcome may be unknown, so let a later reconciliation re-fetch state first.

**Why:** A batch snapshot can become stale when an operator assigns an order concurrently, and retrying an uncertain POST can overwrite a newer operator choice.

**How to apply:** Any automated ShipStation assignee reconciliation must derive the assignee from trusted related records, perform a fresh target-state check, and treat ambiguous network outcomes as retry-later rather than immediate retry.