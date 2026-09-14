# Dashboard Information Architecture Review

## Recommendation

The dashboard should become a short situational-awareness view that answers:

1. What needs attention now?
2. Is the operational data current?
3. Where should the user go to act?

The detailed Weekly Inventory Report should move to a dedicated **Reports** page. The dashboard should retain only a clickable inventory-risk summary.

Inventory should have one canonical workspace. `inventory.html` already combines lot balances, lot assignments, and transaction history, so it should become the primary inventory destination. The overlapping `lot_inventory.html` and `inventory_transactions.html` pages should be redirected only after existing links and bookmarks have been accounted for.

Do not add more detailed tables to the dashboard. Tables, filters, corrections, report composition, recipients, and audit history belong on their relevant destination pages.

## Why this structure fits the product

- The dashboard is used repeatedly and should be optimized for fast scanning rather than detailed analysis.
- The Weekly Inventory Report is data-dense and has several distinct actions. It is difficult to use well inside a dashboard, especially on mobile.
- Current inventory pages overlap, creating uncertainty about which page is authoritative.
- Clickable summaries preserve one-click access to urgent workflows without duplicating their full interfaces.
- Live lot balances and snapshot-oriented report data have different freshness semantics and should not be presented as if they are one data source.

## Proposed navigation

### Operations

1. **Dashboard** — current queues, exceptions, and freshness
2. **Shipments** — picking and ready-to-ship workflow
3. **Inventory** — lot balances, lot assignments, and transaction history
4. **Reports** — inventory risk, shipment history, report runs, and recipients
5. **Charge Report** — financial and unit-charge workflow

### Admin and data

- Order Management
- Shipped Orders
- Order Audit
- Shipped Items
- Bundle SKUs
- Workflow Controls
- Email Contacts
- Inventory Snapshots
- Server Logs
- Report Issue

The existing sidebar restructuring task should own the final navigation grouping. This review only defines the recommended information architecture.

## Reports page

Use one canonical Reports page rather than creating another isolated weekly-report page.

Recommended views:

- **Inventory Risk** — current quantity, pallet breakdown, 52-week average, days left, and risk status
- **Shipment History** — the existing 52-week shipped-history view
- **Report Runs and Recipients** — EOD/EOW/EOM controls, run status, email composition, and recipient management

Role behavior:

- **Viewer:** read-only report access
- **Operations:** read access plus EOD/EOW where currently permitted
- **Admin:** all report actions, including EOM and recipient changes

## Dashboard content

### Keep

- Last updated and Refresh, with an explicit current/stale/error state
- Shipping configuration alerts
- Auto-Ship Day alert when applicable
- FedEx pickup alert when applicable
- A reduced Operational Pulse focused on actionable queues

### Replace with clickable summaries

| Summary | Information | Destination | Urgency behavior |
|---|---|---|---|
| Units to pick | Units, order count, as-of time | Shipments | Escalate when age or volume exceeds an agreed threshold |
| On hold | Held units, order count, oldest hold | Order Management | Warning at any count; critical after agreed age |
| Destination exceptions | Non-zero Benco, Hawaii, Canada, and international counts | Shipments | Show only active groups and escalate near cutoffs |
| New since last ship | Orders, units, last shipment timestamp | Shipments | Warn when volume grows without a recent shipment |
| Inventory risk | At-risk SKU count, soonest days left, most urgent SKU | Reports: Inventory Risk | Critical for zero/negative stock; warning below threshold |
| Lot and data exceptions | Negative balances, quarantine lots, missing assignments where available | Inventory | Critical for negative balances; warning for configuration issues |
| ShipStation freshness | Last sync/reconciliation time and status | Workflow Controls | Explicit stale/critical state after agreed thresholds |

Regional summaries should be grouped or hidden when zero unless the product owner confirms they require constant visibility.

### Remove from the dashboard

- Full Weekly Inventory Report table and mobile card list
- Compose Email and Manage Recipients controls
- EOD, EOW, and EOM controls
- Expanded Time Log form and history
- Always-visible zero-valued regional cards
- Ambiguous “Weekly Reports” wording

## Responsive behavior

### Desktop

- Keep alerts and 6–8 prioritized summaries in the first viewport.
- Make the entire summary card keyboard-accessible and clickable.
- Show the metric, a small supporting fact, freshness, and a clear destination.
- Keep detailed tables and filters on destination pages.

### Mobile

- Order content by urgency: alerts first, then actionable summaries.
- Use full-width cards with at least 44px touch targets.
- Hide zero and non-actionable summaries.
- Do not duplicate the same destinations in both a quick-action dock and the mobile menu.
- Default Reports to Inventory Risk, with Shipment History and report controls available through tabs.

## Implementation sequence

### Phase 1: Canonical destinations

- Create the Reports page and preserve role-based access.
- Establish `inventory.html` as the canonical inventory workspace.
- Update internal inventory links before redirecting legacy pages.
- Coordinate navigation labels and grouping with the existing sidebar restructuring task.

Acceptance:

- Every inventory link lands in one canonical workspace.
- Legacy URLs continue to work.
- Each role sees only the actions it can use.
- Report and inventory data retain clear freshness labels.

### Phase 2: Reports migration

- Move Inventory Risk and report controls from the dashboard to Reports.
- Include existing shipment history without duplicating it.
- Preserve email, copy, run-status, and recipient workflows.

Acceptance:

- There is one detailed Inventory Risk view and one Shipment History view.
- Existing report actions still work for the correct roles.
- Desktop and mobile layouts avoid horizontal scrolling for primary fields.

### Phase 3: Dashboard reduction

- Replace detailed report content with clickable summaries.
- Keep alerts, freshness, and actionable queue information.
- Add explicit loading, empty, stale, and error states.

Acceptance:

- A user can identify the highest-priority queue within ten seconds.
- Every summary leads directly to its relevant workflow.
- No summary displays data without an as-of time or freshness state.

### Phase 4: Legacy cleanup

- Measure use of old inventory routes and dashboard destinations.
- Remove duplicate page implementations only after confirming they are no longer used.

## Risks and tradeoffs

- Moving report controls one level deeper can reduce discoverability. Keep an Inventory Risk summary linking directly to Reports.
- A canonical Inventory page can become dense. Preserve clear tabs and load large histories only when needed.
- Snapshot report values and live lot balances can conflict. Label their source and timestamp rather than blending them.
- Role-specific UI can drift from backend permissions. Verify both together.
- Existing bookmarks may target legacy pages. Redirect before removal.
- Regional cards can imply business priorities that have not been confirmed.

## Product-owner decisions needed

1. Should the destination be called **Reports**, **Operational Reports**, or **Inventory and Reports**?
2. Is the Weekly Inventory Report primarily an operational forecast, an email artifact, or a historical record?
3. What thresholds define urgent pick volume, hold age, inventory risk, and stale ShipStation data?
4. Which regional queues require daily visibility?
5. Should EOD/EOW remain accessible only on Reports, or also have a small dashboard shortcut?
6. Are legacy inventory pages used through bookmarks, training materials, or external links?
7. Is mobile primarily used for warehouse actions, supervisor review, or occasional approval?
8. Should Time Log move to Settings, a personal utility page, or remain outside this redesign?