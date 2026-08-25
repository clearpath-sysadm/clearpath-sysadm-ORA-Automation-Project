---
name: Publish schema alignment
description: Prevent publish-time development-to-production schema diffs from rolling back cancellation inventory safeguards.
---

Before a production publish, development must retain the same cancellation-reversal schema behavior as production:

- `inventory_transactions` accepts the `Cancel` transaction type.
- `lot_balances` credits `Cancel` rows as positive inventory.
- The lot-aware unique line-item index remains present.

**Why:** Replit’s Publish flow uses development as the schema source of truth. If development falls behind on these objects, its generated production migration will attempt to remove production’s working safeguards, which can reject cancellation reversals or make lot balances incorrect.

**How to apply:** When Publish reports database changes unexpectedly, compare development and production schema objects first. Align development to the established production schema and confirm the diff is empty before approving the publish; never approve a migration that removes `Cancel` support.