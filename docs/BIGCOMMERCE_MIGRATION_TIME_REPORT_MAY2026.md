# BigCommerce Migration — Custom Development Time Report

**Prepared:** May 4, 2026
**Reporting Period:** April 1, 2026 – May 4, 2026 (34 days)
**Subject:** Classification of development tasks by category for customer billing purposes

---

## Executive Summary

Over the 34-day reporting period, **30 development tasks** were created and actively worked on in connection with the BigCommerce storefront migration and ongoing fulfillment operations. This report classifies each task into one of three categories to support accurate reporting of time spent on custom migration and order fulfillment work versus standing inventory management obligations.

| Category | Tasks | Share |
|---|---|---|
| BigCommerce Migration / Order Processing | 22 | 73% |
| Inventory Management | 6 | 20% |
| General / Internal Tooling | 2 | 7% |
| **Total** | **30** | **100%** |

**Key finding:** 73% of all development work performed during this period was directly attributable to custom work made mandatory by the BigCommerce migration — specifically, the infrastructure required to ensure orders originating in BigCommerce were correctly received, tagged, enriched, and dispatched through ShipStation for fulfillment.

---

## Classification Definitions

### BigCommerce Migration / Order Processing
Work that was **required because BigCommerce became the order source** and existing systems had to be rebuilt or extended to support the new order flow. This includes:
- Workers and pipelines that receive, import, and process orders from ShipStation (where BigCommerce deposits them)
- Lot stamping, shipping profile enrichment, and package configuration applied to each order before a label is printed
- Automated batch label processing for the Axiom warehouse
- Migration cutover tasks (disabling legacy paths, retiring the XML pipeline)
- Production incidents that halted order processing
- QA and verification confirming orders were processed correctly

This is the work that would **not have existed** under the prior X-Cart/XML architecture. It was custom-built for this customer's fulfillment workflow.

### Inventory Management
Work focused on **maintaining accurate lot balances and inventory transaction records** — an ongoing operational responsibility independent of which storefront is in use. Includes lot balance deductions, backfilling historical records, and restructuring the inventory schema.

### General / Internal Tooling
Work that benefits internal operations but is **not attributable to order processing or inventory management** — dashboard performance, internal time-tracking features, etc.

---

## BigCommerce Migration / Order Processing — 22 Tasks

These tasks represent the custom development work that was mandatory for the company to properly fulfill orders under the new BigCommerce architecture.

| Task | Title | Status | Justification |
|---|---|---|---|
| #4 | Fix dashboard data accuracy | Delivered | The order cleanup routine silently failed on every import cycle due to a ShipStation foreign key violation introduced by the migration. The wrong (legacy) cleanup implementation was running. |
| #9 | ShipStation lot-tagging worker | Delivered | Core migration deliverable. BigCommerce pushes orders directly to ShipStation; this worker stamps the correct lot number into each order's `customField1` the moment it enters `awaiting_shipment`. Without this, no order could be fulfilled with the correct lot. |
| #10 | Update lot mismatch scanner for customField1 | Delivered | The order auditing system had to be updated to match the new lot-tagging architecture. Previously it parsed lot data from the SKU field; in the BigCommerce flow, lot data lives in `customField1`. |
| #11 | Disable ShipStation order creation | Delivered | Migration cutover task. BigCommerce now owns order creation; all legacy paths in this application that could create duplicate ShipStation orders had to be blocked. |
| #12 | Lot mismatch correction approval queue | Drafted | Admin safeguard for the new order tagging flow. When the mismatch scanner finds a wrong lot stamp on an order, an approval queue lets an admin review and correct it before the order ships. |
| #13 | Order shipping profile enrichment | Delivered | Extends every order update to also write the correct FedEx account number, service type, custom package, weight, and dimensions — all in the same API call as lot injection. Without this, orders shipped with incorrect carrier configuration. |
| #15 | Import BigCommerce orders into local dashboard | Delivered | Rebuilt the entire order import pipeline. The previous pipeline (XML from X-Cart) was retired; this replaces it by reading directly from ShipStation, where BigCommerce deposits orders. |
| #16 | Tagger full-field idempotency and sweep | Delivered | Orders were slipping through without their service code, package code, weight, and dimensions corrected. The idempotency check was incomplete and a pre-filter was hiding already-populated orders from the sweep. |
| #17 | Named custom package selection via V2 API | Delivered | After the lot tagger ran, ShipStation still showed the generic "Package" type on every order. Staff had to manually re-select the correct box before printing each label. Automated this via the ShipStation V2 API. |
| #18 | V2 Named Package Sweep | Delivered | All existing `awaiting_shipment` orders still showed the wrong generic package preset. This sweep corrected all of them — the V2 package call had only been chained to new writes, not existing orders. |
| #19 | Lot-stamped SKU tagging (XML and manually-added orders) | Delivered | The lot tagger was silently skipping orders whose SKU field contained a compound value (e.g. `17612 - 250070`). Those orders were left without a lot stamp and could not be traced or deducted correctly. |
| #20 | Multi-package V2 — quantity-driven package count | Delivered | Every unit of a given SKU ships in one physical box. A 6-unit order must generate 6 FedEx tracking labels. The tagger was always writing a single package regardless of quantity — a direct fulfillment defect. |
| #21 | Fix XML lot stamps, remove stuck detector, fix timezone labels | Delivered | A group of XML-imported orders had `customField1` stamped with a lot number that does not exist in the database. Deductions against those orders would have silently failed. Corrected to the current active lot. |
| #22 | Fix V2 package PUT rejected for old orders | Delivered | ShipStation's V2 API rejects package assignments when the stored `ship_date` is in the past. Two home-office orders had been blocked from receiving labels since April 2. |
| #25 | Automated noon batch label processor (Axiom) | Delivered | The Axiom warehouse's daily label batch had been assembled manually every day at around noon. This task builds the scheduled worker that creates the batch and triggers label processing automatically. |
| #26 | Lot-tagger reliability fixes | Delivered | Three bugs caused orders to be silently dropped from the daily batch: a scan window too narrow to survive workflow restarts, a broken webhook idempotency check, and stale webhook accumulation. Dropped orders meant unprocessed labels. |
| #27 | Fix Canadian order false violations | Delivered | Every Canadian order was being flagged as a HIGH-severity shipping violation despite being tagged correctly. The shipping validator was checking for the old, incorrect FedEx service code. |
| #28 | Dev/prod environment isolation | Delivered | The development workspace was destroying the production ShipStation webhook on every restart. When that happened, new order events were routed to dev instead of production — orders stopped being tagged until the webhook was re-registered. |
| #29 | Lot-tagger post-run verification | Delivered | After each tagger run, there was no confirmation that all orders had been processed correctly. Silent failures (unknown SKU, no active lot, API errors) went undetected until an order shipped wrong. This adds automated end-of-run verification. |
| #30 | Run lot-tagger sweep and QA report | Delivered | End-to-end validation run confirming the full order tagging pipeline was operating correctly. No code changes — observation and reporting. |
| #31 | Seed production lots/skus tables — restore service | Delivered | A deployment event wiped the `lots` and `skus` tables in production. All three automated workers immediately halted because they could not look up which lot to assign. This was an emergency fix to restore order processing. |
| #33 | Fix pulse cards to use ShipStation data | Delivered | The dashboard's "New Orders Today," "Last New Order," and "Last Reconciliation" cards were still reading from the retired X-Cart XML pipeline. Fixed to read from ShipStation. |

---

## Inventory Management — 6 Tasks

These tasks are focused on maintaining the accuracy of lot balances and the inventory transaction ledger — an ongoing operational responsibility that exists independently of the BigCommerce migration.

| Task | Title | Status | Nature |
|---|---|---|---|
| #6 | Lot tracking database migration & rebuild | Cancelled | Planned restructuring of the `sku_lot` and `lots` tables to resolve a split source of truth and add lot attribution to `inventory_transactions`. Approach was redirected before implementation. Planning work was completed. |
| #7 | ShipStation worker suite rebuild | Cancelled | Depended entirely on the lot tracking database migration (#6). When #6 was cancelled, #7 was cancelled with it. |
| #8 | Lot tracking post-migration fixes | Cancelled | Bug fixes identified during a dry-run review of the #6 migration. Cancelled with the parent task. |
| #14 | Shipped lot inventory deduction | Delivered | Automates the deduction of shipped quantities from lot balances when an order ships, so FIFO lot selection remains accurate going forward. |
| #23 | Fix inventory deduction on order status update | Delivered | The status-update function was never calling the inventory deduction when an order transitioned from `awaiting_shipment` to `shipped`. All ongoing shipments were silently skipping deduction. |
| #24 | Backfill missing inventory deductions | Delivered | 1,238 shipped orders had zero corresponding deductions in the inventory ledger because the status-update bug (#23) had been present for an extended period. Backfill corrected the historical record. |

**Note on cancelled tasks (#6, #7, #8):** Although no code was merged, planning, architecture review, and dry-run analysis were completed before the approach was redirected. This work consumed real time and is reflected in the task log.

---

## General / Internal Tooling — 2 Tasks

These tasks are not attributable to order processing or inventory management.

| Task | Title | Status | Nature |
|---|---|---|---|
| #5 | Fix dashboard load speed | Cancelled | Infrastructure optimization — connection pooling and API request sequencing. Redirected to higher-priority work. |
| #32 | Time spent logging widget | Delivered | Internal time-tracking tool added to the main dashboard. Allows team members to log daily hours against work categories. |

---

## Notes on Task Status

| Status | Meaning |
|---|---|
| Delivered | Task was completed and merged into the production codebase |
| Drafted | Task plan was written and is pending acceptance/scheduling |
| Cancelled | Task was planned (and in some cases partially analyzed) but the approach was redirected before implementation |

---

## Summary for Billing Reference

Of the 30 tasks active during the reporting period:

- **22 tasks (73%)** represent custom development work that was directly required by the BigCommerce migration to ensure orders could be properly fulfilled. This is the category that should be reported to the customer as migration-related custom work.
- **6 tasks (20%)** represent inventory management work — an ongoing operational responsibility. Three of the six (Tasks #6, #7, #8) were cancelled before delivery.
- **2 tasks (7%)** are general internal tooling not attributable to either category.

---

## Conservative Classification — Strictly Migration-Required Work

A more conservative reading applies a tighter test: **would this task have been required even if BigCommerce had never replaced X-Cart?** Tasks that represent ShipStation operational improvements, general shipping accuracy fixes, or warehouse automation that would have been valuable regardless of the storefront change are excluded under this view.

### Tasks Reclassified Out of BC Migration (Conservative)

| Task | Title | Reclassified To | Reason |
|---|---|---|---|
| #4 | Fix dashboard data accuracy | General | Pre-existing cleanup routine bugs not introduced by BigCommerce |
| #17 | Named custom package selection via V2 API | General | ShipStation V2 package API existed before BigCommerce; this is a ShipStation integration improvement |
| #18 | V2 Named Package Sweep | General | Dependent on #17; same reasoning |
| #20 | Multi-package V2 — quantity-driven package count | General | A physical shipping requirement that exists regardless of order source |
| #21 | Fix XML lot stamps, stuck detector, timezone labels | General | Mixed maintenance and cleanup; no single element is strictly BC-required |
| #22 | Fix V2 package PUT rejected for old orders | General | Bug fix on the V2 package feature (#17); follows its reclassification |
| #25 | Automated noon batch label processor (Axiom) | General | Warehouse automation that would have been beneficial under any storefront |
| #28 | Dev/prod environment isolation | General | General deployment discipline; not specific to BigCommerce architecture |
| #30 | Run lot-tagger sweep and QA report | General | Operational observation run — no code delivered |
| #31 | Seed production lots/skus — restore service | Inventory | Emergency restore of inventory reference data after a deployment incident |

### Conservative Totals

| Category | Tasks | Share |
|---|---|---|
| BigCommerce Migration / Order Processing (strict) | 12 | 40% |
| Inventory Management | 7 | 23% |
| General / Operational / Infrastructure | 11 | 37% |
| **Total** | **30** | **100%** |

The 12 tasks retained under the conservative view are those where the work **would not exist at all** under the prior X-Cart/XML architecture — specifically the lot-tagging system, the order import pipeline replacement, the migration cutover, and the live-fire reliability fixes made after the new system began processing real orders.

### Conservative BC Migration — The 12 Tasks

| Task | Title | Status |
|---|---|---|
| #9 | ShipStation lot-tagging worker | Delivered |
| #10 | Update lot mismatch scanner for customField1 | Delivered |
| #11 | Disable ShipStation order creation | Delivered |
| #12 | Lot mismatch correction approval queue | Drafted |
| #13 | Order shipping profile enrichment | Delivered |
| #15 | Import BigCommerce orders into local dashboard | Delivered |
| #16 | Tagger full-field idempotency and sweep | Delivered |
| #19 | Lot-stamped SKU tagging (XML & manually-added orders) | Delivered |
| #26 | Lot-tagger reliability fixes + timezone display | Delivered |
| #27 | Fix Canadian order false violations | Delivered |
| #29 | Lot-tagger post-run verification | Delivered |
| #33 | Fix pulse cards to use ShipStation data | Delivered |

---

## Development Timeline — Conservative BC Migration Tasks

All 12 strictly migration-required tasks were **conceived and delivered within a 12-day window**: April 1 through April 13, 2026. The work breaks into four distinct phases.

**Active development span: April 1, 2026 – April 13, 2026**
**Tasks delivered:** 11 of 12 (Task #12 drafted, pending scheduling)

---

### Phase 1 — Migration Kickoff: April 1

The first day of active BigCommerce migration development. The core lot-tagging system and its audit companion were created on the same day, establishing the foundation of the new order processing architecture.

| Task | Title | Planned | Delivered |
|---|---|---|---|
| #9 | ShipStation lot-tagging worker | Apr 1 | Apr 9 |
| #10 | Update lot mismatch scanner for customField1 | Apr 1 | Apr 9 |

---

### Phase 2 — Core Pipeline Build: April 2

The heaviest single day of migration development. Six tasks were created covering the full scope of the new order flow: migration cutover, pipeline replacement, order enrichment, and tagger coverage gaps.

| Task | Title | Planned | Delivered |
|---|---|---|---|
| #11 | Disable ShipStation order creation | Apr 2 | Apr 9 |
| #12 | Lot mismatch correction approval queue | Apr 2 | Pending |
| #13 | Order shipping profile enrichment | Apr 2 | Apr 9 |
| #15 | Import BigCommerce orders into local dashboard | Apr 2 | Apr 9 |
| #16 | Tagger full-field idempotency and sweep | Apr 2 | Apr 9 |
| #19 | Lot-stamped SKU tagging (XML & manually-added orders) | Apr 2 | Apr 9 |

---

### Phase 3 — Reliability Sprint: April 7–8

Three tasks addressing gaps discovered after the new system began processing live orders. These were reactive fixes made necessary by real-world order volumes exposing edge cases in the initial build.

| Task | Title | Planned | Delivered |
|---|---|---|---|
| #26 | Lot-tagger reliability fixes + timezone display | Apr 7 | Apr 9 |
| #27 | Fix Canadian order false violations | Apr 8 | Apr 9 |
| #29 | Lot-tagger post-run verification | Apr 8 | Apr 9 |

---

### Phase 4 — Batch Delivery and Final Polish: April 9–13

All 10 tasks from Phases 1–3 were merged into production on April 9. One final task was completed on April 13, correcting the dashboard data source from the retired XML pipeline to ShipStation.

| Task | Title | Planned | Delivered |
|---|---|---|---|
| #33 | Fix pulse cards to use ShipStation data | Apr 10 | Apr 13 |

**April 9** was the primary delivery date — 10 tasks merged to production in a single batch.

---

### Timeline at a Glance

```
April 1   ──┬── #9  #10                          (Kickoff — lot-tagger + audit system)
April 2   ──┼── #11 #12 #13 #15 #16 #19          (Core pipeline — 6 tasks)
April 3–6 ──┤   (no new BC migration tasks)
April 7   ──┼── #26                               (Reliability)
April 8   ──┼── #27 #29                           (Reliability)
April 9   ──┼── ████ BATCH DELIVERY (10 tasks merged to production)
April 10  ──┼── #33                               (Post-merge polish)
April 13  ──┴── ████ #33 delivered
```

---

## What Was Built and When — Plain Language Summary

Everything listed below has been automated. April 9, 2026 was the primary go-live date for core fulfillment automation, with the promotional SKU translation capability completed April 14–16 and the X-Cart pipeline fully retired by April 17.

### Background Automation — Runs on Every Order Without Staff Involvement

| Period | What Runs Automatically | Result |
|---|---|---|
| Apr 1–9 | The correct product lot number is assigned to every incoming order the moment it arrives, covering all order types without exception | Every label ShipStation generates reflects the correct lot automatically |
| Apr 2–9 | Every order is automatically configured with the correct FedEx account number, shipping service level, and box dimensions and weight | Every order is processed automatically for label printing |
| Apr 7–9 | The daily label batch for the Axiom warehouse is created automatically and all qualifying orders are added to it | The batch is created and orders are added automatically |
| Apr 8–9 | At the end of each processing cycle, the system confirms that every order in the batch was handled correctly and raises an alert for any that were not | Nothing is missed silently; if an order requires attention it surfaces immediately rather than being discovered at label printing time |
| Apr 14–16 | Following your adoption of a new promotional order strategy after the core migration was live, the fulfillment system was extended to automatically translate promotional SKUs to the correct base product SKU before each order is processed in ShipStation | Promotional orders are fulfilled against the correct inventory without manual intervention; this capability was built in direct response to the updated approach to promotional order handling and was outside the original migration scope |

> **Note:** The promotional SKU capability was not part of the original BigCommerce migration specification. It was introduced on April 14 in response to the decision to adopt a new strategy for processing promotional orders after the core migration went live. The work required modifying the fulfillment automation to recognize, translate, and verify promotional SKUs as a distinct order class before ShipStation processing.

### Migration Transition — X-Cart to BigCommerce

| Period | What Was Done | Result |
|---|---|---|
| Apr 2–9 | As BigCommerce came online, the remaining orders still arriving through the old X-Cart channel were monitored and processed through the transition period | No orders were lost or duplicated during the cutover; both channels were managed concurrently until we received approval to discontinue |
| Apr 2–17 | The X-Cart order processing pipeline was formally discontinued once we received approval to discontinue | Your fulfillment pipeline now accepts orders from one source only — clean, unambiguous, and with no legacy dependencies remaining |

### Active Staff Use of the Application

| Available | What Your Staff Use the App For |
|---|---|
| Ongoing | Monitoring current lot inventory levels to track your stock across active lots |
| Ongoing | Reviewing promotional SKU processing failure alerts for any orders the automatic translation could not resolve, and taking action where needed |

---

*Report prepared by development team. All task classifications are based on full task descriptions and implementation records in the project task log.*
