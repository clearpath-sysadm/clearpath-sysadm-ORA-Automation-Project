---
name: ShipStation missing-order lifecycle
description: How to handle local active orders that no longer exist in ShipStation.
---

Treat a definitive ShipStation 404 during status reconciliation as a preserved, non-pickable local state. Do not delete the row or hide active orders with a blanket age filter.

**Why:** The incremental watermark feed does not prove current membership, so a missed status event can leave a local order active indefinitely. The shared API wrapper raises an HTTP error for 404 responses, so reconciliation must classify that exception explicitly rather than relying only on returned response objects.

**How to apply:** When changing order reconciliation or active-order reports, keep missing records available for audit while excluding them from pick, shipment, and other open-order totals. Confirmed-open old orders must remain visible.