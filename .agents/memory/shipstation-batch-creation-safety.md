---
name: ShipStation batch creation safety
description: Safety rules for creating, recovering, and cleaning up ShipStation batches.
---

Treat ShipStation batch creation as non-idempotent. Claim the intended operation durably before sending it, use a stable external identity, and never automatically repeat a POST after an ambiguous response. Recover by external identity and original membership instead.

**Why:** ShipStation can accept a create even when the caller receives an uncertain result. A retry can create a duplicate, while later ShipStation operations can move every shipment to a replacement and leave the verified source open and empty.

**How to apply:** Serialize creators with a deterministic database lock, retain claims for timeouts, server errors, and malformed success responses, and release them only for explicit client rejection. Reconcile later without blocking creation. Destructive cleanup requires two delayed observations, an explicit valid zero count, and raw proof that every original shipment belongs to exactly one identical replacement distinct from the source. If the replacement changes, restart the delay. Send DELETE only once; ambiguous failures must be rechecked through the full reconciliation path rather than retried at the HTTP layer.