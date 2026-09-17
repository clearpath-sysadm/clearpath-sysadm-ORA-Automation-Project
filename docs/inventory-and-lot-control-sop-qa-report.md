# Inventory and Lot Control SOP — Codebase QA Report

## Document reviewed

- **File:** `attached_assets/05_Inventory_and_Lot_Control_SOP_-_Write_1789658312577.docx`
- **SOP ID:** ORA-APP-SOP-001
- **Revision:** Rev 01
- **Status reviewed:** Draft for approval

## QA verdict

**REJECT — revise before approval**

The SOP is generally well structured, but several instructions do not accurately describe the current application or its safeguards.

## Critical findings

### 1. Lot deletion consequences need stronger, more precise language

**SOP wording**

> Deleting a lot removes all transactions linked to it and clears its references from shipped line items.

**Code behavior**

- Permanently deletes every inventory transaction linked to the lot.
- Sets `lot_id` to `NULL` on associated ShipStation order-line records.
- Does not delete the shipped orders or items themselves.

This destroys the lot's inventory audit trail and removes lot traceability from affected order lines.

**Recommended wording**

> Deleting a lot permanently deletes all inventory transactions linked to it and removes the lot reference from associated ShipStation order-line records. It does not delete the orders or shipped items. Prefer correction, quarantine, deactivation, or depletion unless Quality specifically approves permanent deletion.

**Code reference:** `app.py:7969-7990`

### 2. Deletion approval is not enforced or recorded by the app

The SOP correctly requires documented approval, but the application does not capture or validate that approval. The endpoints check the Admin role and then perform the deletion. They do not require an approval reason or preserve approval evidence.

**Recommended addition**

> Approval must be obtained and retained outside the app. The app does not require or record the approval before deletion.

**Code references:** `app.py:2639-2689`, `app.py:7969-7993`

### 3. Negative initial quantities are not safely rejected by the backend

Section 4.2 says Initial Quantity must be positive or zero. The backend accepts a negative integer. It creates the lot but does not create an opening receipt, which can mislead the operator.

The SOP should treat this as a current application limitation, not an enforced validation.

**Recommended wording**

> Enter 0 or a positive whole number. Do not enter a negative value. If a negative value is accepted, stop and escalate because the current application does not reliably reject it.

**Code reference:** `app.py:7811-7867`

## High-priority findings

### 4. Incorrect success message for adding a lot

- **SOP:** “Lot added successfully”
- **Actual response:** “Lot created successfully”

**Code reference:** `app.py:7871-7881`

### 5. The 200-unit receipt safeguard does not verify a supplier lot number

The application checks that Notes is nonblank and does not contain certain administrative phrases. It does not determine whether the entered text is a real supplier lot number.

**Recommended wording**

> For receipts of 200 units or more, Notes must contain the actual supplier lot number. The app rejects blank Notes and certain administrative phrases, but the operator remains responsible for verifying the lot number against the source record.

**Code reference:** `app.py:2423-2449`

### 6. Negative balances are permitted

The SOP correctly tells operators not to create unexplained negative balances, but the application does not enforce that rule. An `Adjust Down` can be saved successfully even if the resulting balance is negative.

**Recommended addition**

> The app may permit a negative resulting balance. Calculate the expected balance before saving, and stop and escalate if the result would be negative.

**Code reference:** `app.py:7998-8086`

### 7. Lot Assignments edits change the underlying lot record

The Lot Assignments tab is not backed by a separate assignment record. It manages the underlying SKU–lot records. Editing an assignment can change the lot's SKU, lot number, or active status.

**Recommended control**

> The Lot Assignments tab manages the underlying SKU–lot record. Changing the SKU or lot number changes the lot's identity; it is not merely an order-routing preference. Verify existing inventory and transaction history before editing these fields.

**Code reference:** `app.py:5110-5170`

### 8. Assignment success-message guidance is incomplete

The SOP says assignment actions may reload without a success message. The API returns messages such as “SKU-Lot updated successfully.”

Require both the success response, when displayed, and verification of the resulting row.

**Code reference:** `app.py:5170`

## Medium-priority clarifications

### 9. Backorder retry warning is accurate but incomplete

A positive receipt or `Adjust Up` can schedule a background retry after the inventory commit. For a newly created lot, the retry occurs only when the opening quantity is positive and the lot is Active. The retry may already be running or may fail asynchronously.

**Recommended wording**

> Saving a positive Receive or Adjust Up—or creating an Active lot with a positive opening quantity—can immediately schedule a background retry of unresolved, awaiting-shipment backorders for that SKU. Scheduling does not prove the retry completed successfully.

**Code references:** `app.py:264-323`, `app.py:2480-2493`, `app.py:7876-7880`, `app.py:8081-8085`

### 10. Historical transaction results are limited

Inventory transaction queries return at most 1,000 records. The SOP should warn that a record absent from a broad search may require narrower date and SKU filters.

**Code reference:** `app.py:2280-2325`

### 11. Reactivation wording should distinguish UI from backend enforcement

The backend rejects reactivation of a depleted lot when its balance is zero. The confirmation dialog is a UI control, not a server-side confirmation requirement. The underlying restriction is accurate.

**Code reference:** `app.py:7891-7955`

## Confirmed accurate

- Any signed-in user may view these records.
- Operations and Admin may add or edit transactions and lots.
- Permanent deletion is Admin-only.
- Received Date controls displayed FIFO ordering.
- `Receive`, `Adjust Up`, and `Repack` add to a lot balance.
- `Ship` and `Adjust Down` reduce a lot balance.
- Receive and adjustment transactions require a selected lot.
- Duplicate SKU–lot combinations are rejected.
- Lot metadata editing is limited to Received Date, Status, and Notes.
- Assignments do not receive inventory or directly change balances.
- The escalation guidance for missing information, 401/403 responses, and incorrect post-save results is appropriate.

## Release recommendation

Correct findings 1–8 before Quality approval. Findings 9–11 should also be incorporated to prevent operator misunderstanding.