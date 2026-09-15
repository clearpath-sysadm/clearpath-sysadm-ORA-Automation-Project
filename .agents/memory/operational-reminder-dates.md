---
name: Operational reminder dates
description: Timezone and persistence rules for date-based dashboard reminders.
---

Calculate operational reminder dates on the server in America/Chicago rather than from each viewer's browser. Alerts triggered by crossing a metric threshold must latch durable daily state and remain pending until explicitly completed, even when the live metric later falls.

**Why:** Browser timezones made Auto Ship reminders unreliable, and the FedEx reminder disappeared after processing reduced the live units-to-ship count below its trigger.

**How to apply:** Use the shared Central Time helper for dashboard date rules and completion records. Any future threshold-based operational reminder should record the threshold crossing at the metric writer, not infer history from the current value.