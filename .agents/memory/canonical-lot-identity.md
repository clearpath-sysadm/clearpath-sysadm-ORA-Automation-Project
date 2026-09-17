---
name: Canonical lot identity
description: Rules for changing the SKU or lot number attached to a canonical lot record.
---

SKU and lot number are historical identity, not operational routing preferences. Normal lot edits may change status only. Identity correction requires an audited admin flow and is allowed only when the lot has zero balance and no transactions, order-line links, reservations, alerts, or lifecycle history.

**Why:** Inventory history links to the canonical lot identifier while also retaining denormalized identity text. Reassigning or renaming a used lot can silently reinterpret history and create contradictory records.

**How to apply:** New lot-management features must preserve identity immutability, use deterministic advisory-lock ordering before row locks, reject stale writes, and direct operators to create a new lot plus archive/inactivate the old one whenever history exists.