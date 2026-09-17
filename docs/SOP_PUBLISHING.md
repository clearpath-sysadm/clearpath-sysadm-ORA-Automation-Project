# SOP publishing

The Help & Training library is generated from four fixed controlled DOCX sources:

- `docs/Inventory_and_Lot_Control_SOP_Rev_02.docx` — ORA-APP-SOP-001, Rev 02
- `deliverables/app-sop-templates/06_Order_Corrections_and_Cancellations_SOP.docx` — ORA-APP-SOP-002, Rev 01
- `deliverables/app-sop-templates/07_Daily_Fulfillment_and_Pick_List_SOP.docx` — ORA-APP-SOP-003, Rev 01
- `deliverables/app-sop-templates/08_Period_End_Reporting_SOP.docx` — ORA-APP-SOP-004, Rev 01

The packaged Inventory Rev 01 file is superseded and is intentionally not an input.

The Period-End Reporting Rev 01 source does not contain the front-page draft banner found in the other three files. Its control tables still explicitly say `Upon approval`, `Quality`, `Pending`, and `approval copy not yet released`. The publisher requires that complete combination and rejects any conflicting banner before deriving the common `DRAFT FOR APPROVAL` library status.

Run:

```sh
python scripts/publish_sops.py
```

The command writes matching web JSON and PDF files to `generated/sops/`. It exits with an error if a source is missing, its ID/revision or draft metadata changes unexpectedly, or required headings, numbered procedures, or warning content are missing. The generated files are committed so a missing artifact is an explicit server error rather than an automatic runtime fallback.

Before publishing a changed source, reconcile its instructions against current page labels, role enforcement, action timing, side effects, correction/archive behavior, and retired routes. Drafts must remain labeled `DRAFT FOR APPROVAL`, effective `Upon approval`, with Quality approval pending until approval evidence exists.