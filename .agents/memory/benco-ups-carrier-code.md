---
name: Benco UPS carrier code
description: The correct ShipStation carrier code for UPS in this account, discovered during live testing of the Benco third-party billing switch.
---

# Benco UPS Carrier Code

The ShipStation carrier code for UPS in this account is **`ups_walleted`** ("UPS by ShipStation"), NOT `ups`.

**Why:** Discovered during live test of order 864891 — sending `carrier_code='ups'` returned `{"Message":"Invalid serviceCode"}` (HTTP 400). Querying `/carriers` confirmed the only UPS entry is `code='ups_walleted'`, `shippingProviderId=556331`.

**How to apply:** Any code that sets or compares the UPS carrier code must use `ups_walleted`. The service code `ups_ground` is correct and accepted. The tagger (`resolve_shipping_profile`), shipping validator (`BENCO_EXPECTED_CARRIER`), and any future carrier-code comparisons must all use `ups_walleted`.

**Confirmed working (2026-08-05):** After the fix, ShipStation accepted the order update and returned:
- `carrierCode: 'ups_walleted'`
- `serviceCode: 'ups_ground'`
- `billToParty: 'third_party'`
- `billToAccount: '10642V'`
- `billToPostalCode: '18640'`
- `billToCountryCode: 'US'`
- `billToMyOtherAccount: 556331` — auto-populated by ShipStation with the ups_walleted shippingProviderId; not a concern, mismatch checker ignores it for third_party orders.

Mismatch check returned `[]` after update — no re-write loop.
