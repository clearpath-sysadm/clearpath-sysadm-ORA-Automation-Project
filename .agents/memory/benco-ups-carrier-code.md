---
name: Benco UPS carrier code
description: The correct ShipStation carrier code for Acxiom's directly-connected UPS account, and why ups_walleted must never be used for Benco third-party billing.
---

# Benco UPS Carrier Code

Acxiom's directly-connected UPS account has carrier code **`ups`** (nickname "Axiom", account number `3R25Y3`, shippingProviderId `732888`).

**Why:** `ups_walleted` is ShipStation's own UPS account ("UPS by ShipStation"). Using it requires a ShipStation credit card on file and does NOT route billing to an external UPS account — it bills ShipStation's account. Third-party billing to Benco's UPS account (10642V) requires Acxiom's own directly-connected UPS account (`code='ups'`).

**How to apply:** Any code setting or comparing the UPS carrier code for Benco orders must use `ups`. Service code `ups_ground` is correct for both the walleted and direct accounts. The tagger (`resolve_shipping_profile`), shipping validator (`BENCO_EXPECTED_CARRIER`), and any future carrier-code comparisons must use `ups`.

**Third-party billing fields (Benco):**
- `billToParty: 'third_party'`
- `billToAccount`: from `BENCO_UPS_ACCOUNT_NUMBER` env var (`10642V`)
- `billToPostalCode`: from `BENCO_UPS_POSTAL_CODE` env var (`18640`)
- `billToCountryCode`: from `BENCO_UPS_COUNTRY_CODE` env var (`US`)
