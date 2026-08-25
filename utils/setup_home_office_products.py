#!/usr/bin/env python3
"""
One-time utility: create or update ShipStation product records for Home Office SKUs.
Ensures both the required product name and warehouseLocation = "Home Office" on each SKU.

ShipStation V1 has no POST /products endpoint — product records are only
created when orders containing that SKU flow through the system. For SKUs that
don't exist yet, the script creates a minimal on-hold placeholder order, which
causes ShipStation to create the product record, then immediately updates its
name and warehouse location and deletes the placeholder order.

Usage:
    python utils/setup_home_office_products.py           # live run
    python utils/setup_home_office_products.py --dry-run # preview only
"""

import os
import sys
import argparse
import base64
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# ShipStation allows 40 requests per minute.  We aim for ≈20 req/min to stay
# comfortably under the limit, then back off automatically on any 429.
_INTER_REQUEST_SLEEP = 2.0   # seconds between every API call (~30 req/min, limit is 40)
_RATE_LIMIT_BACKOFF  = 65.0  # seconds to wait after a 429 before retrying


def _request(method: str, url: str, headers: dict, **kwargs) -> requests.Response:
    """
    Thin wrapper around requests.<method> that:
    - sleeps _INTER_REQUEST_SLEEP before every call
    - retries up to 3 times on 429, honouring the Retry-After header when present
    """
    time.sleep(_INTER_REQUEST_SLEEP)
    for attempt in range(3):
        resp = getattr(requests, method)(url, headers=headers, **kwargs)
        if resp.status_code != 429:
            return resp
        retry_after = float(resp.headers.get("Retry-After", _RATE_LIMIT_BACKOFF))
        wait = max(retry_after, _RATE_LIMIT_BACKOFF)
        print(f"    (rate limited — waiting {wait:.0f}s before retry {attempt + 1}/3…)", flush=True)
        time.sleep(wait)
    # return the last 429 response so the caller can surface the error
    return resp


# ---------------------------------------------------------------------------
# Config (SKUs)
# ---------------------------------------------------------------------------

SHIPSTATION_V1_BASE = "https://ssapi.shipstation.com"
WAREHOUSE_LOCATION = "Home Office"

# (sku, display_name)
PRODUCTS = [
    ("18565-25",      "Tongue Razor 25-pack"),
    ("18565-50",      "Tongue Razor 50-pack"),
    ("18565-100",     "Tongue Razor 100-pack"),
    ("18680",         "Free Sample"),
    ("18680-OC-TP",   "Free Sample — OraCare & OraPro Paste"),
    ("18680-OC",      "Free Sample — OraCare only"),
    ("18680-ORTH-TP", "Free Sample — Ortho Protect & OraPro Paste"),
    ("18680-ORTH",    "Free Sample — Ortho Protect only"),
    ("18680-TP",      "Free Sample — OraPro Paste Only"),
    ("18682",         "Poster"),
    ("18682-6",       "Poster — Value Pack of 6"),
    ("18682-BB",      "Poster — Bad Breath"),
    ("18682-OR",      "Poster — Oral Health Quiz"),
    ("18682-FL",      "Poster — Flossing"),
    ("18682-PR",      "Poster — Protected by PreRinse"),
    ("18682-HHG",     "Poster — Happy Healthy Gums"),
    ("18682-DM",      "Poster — Dry Mouth"),
]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _build_headers() -> dict:
    api_key = os.getenv("SHIPSTATION_API_KEY")
    api_secret = os.getenv("SHIPSTATION_API_SECRET")
    if not api_key or not api_secret:
        print("ERROR: SHIPSTATION_API_KEY / SHIPSTATION_API_SECRET environment variables not set.")
        sys.exit(1)
    encoded = base64.b64encode(f"{api_key}:{api_secret}".encode()).decode()
    return {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def find_product_by_sku(sku: str, headers: dict) -> dict | None:
    """
    Returns an active matching product first, then an inactive matching product,
    whose SKU exactly matches (case-insensitive), or None if not found.

    Inactive products are included so a prior setup run remains idempotent even
    if ShipStation later deactivated the product.
    """
    resp = _request(
        "get",
        f"{SHIPSTATION_V1_BASE}/products",
        headers=headers,
        params={"sku": sku, "showInactive": "true", "pageSize": 25},
        timeout=20,
    )
    if resp.status_code != 200:
        raise RuntimeError(
            f"GET /products?sku={sku} returned {resp.status_code}: {resp.text[:300]}"
        )
    products = resp.json().get("products", [])
    matches = [
        product for product in products
        if (product.get("sku") or "").strip().upper() == sku.strip().upper()
    ]
    if not matches:
        return None
    return sorted(matches, key=lambda product: not bool(product.get("active", True)))[0]


def update_product(product_id: int, existing: dict, name: str, headers: dict) -> dict:
    """
    PUT /products/{productId} — sets the required name and warehouse location
    while preserving all other fields.
    """
    payload = {
        **existing,
        "name": name,
        "warehouseLocation": WAREHOUSE_LOCATION,
    }
    resp = _request(
        "put",
        f"{SHIPSTATION_V1_BASE}/products/{product_id}",
        headers=headers,
        json=payload,
        timeout=20,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"PUT /products/{product_id} returned {resp.status_code}: {resp.text[:300]}"
        )
    return resp.json()


def verify_product_configuration(product: dict | None, sku: str, expected_name: str) -> dict:
    """Require a read-back product to match the required name and location."""
    if not product:
        raise RuntimeError("product was not found during post-update verification")

    actual_name = (product.get("name") or "").strip()
    actual_location = (product.get("warehouseLocation") or "").strip()
    if actual_name != expected_name or actual_location != WAREHOUSE_LOCATION:
        raise RuntimeError(
            f"verification failed for {sku}: expected name={expected_name!r}, "
            f"warehouseLocation={WAREHOUSE_LOCATION!r}; got "
            f"name={actual_name!r}, warehouseLocation={actual_location!r}"
        )
    return product


def _product_result(
    sku: str,
    action: str,
    product: dict | None,
    product_id: int | str | None,
    ok: bool,
    expected_name: str,
    error: str | None = None,
) -> dict:
    """Build a report-safe result without credentials or order data."""
    result = {
        "sku": sku,
        "action": action,
        "product_id": product_id,
        "active": product.get("active") if product else None,
        "name": (product.get("name") or "").strip() if product else None,
        "warehouse_location": product.get("warehouseLocation") if product else None,
        "expected_name": expected_name,
        "expected_warehouse_location": WAREHOUSE_LOCATION,
        "ok": ok,
    }
    if error:
        result["error"] = error
    return result


def _write_report(report_path: str, results: list[dict], dry_run: bool) -> None:
    """Persist a verifiable per-SKU result for the most recent run."""
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ok_count = sum(1 for result in results if result["ok"])
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dry_run": dry_run,
        "warehouse_location": WAREHOUSE_LOCATION,
        "summary": {
            "total": len(results),
            "succeeded": ok_count,
            "failed": len(results) - ok_count,
        },
        "products": results,
    }
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nPer-SKU report written to {path}")


def create_placeholder_order(sku: str, name: str, headers: dict) -> int:
    """
    Creates a minimal on-hold placeholder order containing the target SKU.
    ShipStation creates the product record automatically when the order is ingested.
    Returns the ShipStation orderId.
    """
    order_number = f"PROD-SETUP-{sku.replace('-', '')}-{int(time.time())}"
    payload = {
        "orderNumber": order_number,
        "orderDate": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.0000000"),
        "orderStatus": "on_hold",
        "internalNotes": "AUTO-GENERATED placeholder for product setup. Safe to delete.",
        "customerEmail": "setup@oracare.com",
        "billTo": {
            "name": "Product Setup Placeholder",
            "street1": "123 Placeholder St",
            "city": "Minneapolis",
            "state": "MN",
            "postalCode": "55401",
            "country": "US",
        },
        "shipTo": {
            "name": "Product Setup Placeholder",
            "street1": "123 Placeholder St",
            "city": "Minneapolis",
            "state": "MN",
            "postalCode": "55401",
            "country": "US",
        },
        "items": [
            {
                "sku": sku,
                "name": name,
                "quantity": 1,
                "unitPrice": 0,
            }
        ],
    }
    resp = _request(
        "post",
        f"{SHIPSTATION_V1_BASE}/orders/createorder",
        headers=headers,
        json=payload,
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"POST /orders/createorder returned {resp.status_code}: {resp.text[:300]}"
        )
    order_id = resp.json().get("orderId")
    if not order_id:
        raise RuntimeError("createorder succeeded but returned no orderId")
    return order_id


def delete_order(order_id: int, headers: dict):
    """
    DELETE /orders/{orderId} — removes the placeholder order.
    Raises on failure so the caller can preserve the original error while
    reporting any failed cleanup.
    """
    resp = _request(
        "delete",
        f"{SHIPSTATION_V1_BASE}/orders/{order_id}",
        headers=headers,
        timeout=20,
    )
    if resp.status_code not in (200, 204):
        raise RuntimeError(
            f"could not delete placeholder order {order_id} — HTTP {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Create or update ShipStation product records for Home Office SKUs"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without making any API changes",
    )
    parser.add_argument(
        "--report",
        default="logs/home_office_products_last_run.json",
        help="Path for the per-SKU result report (default: logs/home_office_products_last_run.json)",
    )
    args = parser.parse_args()
    dry_run: bool = args.dry_run

    headers = _build_headers()

    print()
    print("ShipStation Home Office Product Setup")
    print("=" * 80)
    if dry_run:
        print("DRY RUN — no changes will be made")
        print("=" * 80)
    print()

    col_sku    = 22
    col_action = 16
    col_id     = 16
    print(f"{'SKU':<{col_sku}}{'Action':<{col_action}}{'SS Product ID':<{col_id}}Status")
    print("-" * 80)

    results = []

    for sku, name in PRODUCTS:
        try:
            existing = find_product_by_sku(sku, headers)
            time.sleep(0.35)  # stay under ShipStation's rate limit

            if existing:
                # ── Product already exists ──
                product_id = existing.get("productId", "?")
                current_name = (existing.get("name") or "").strip()
                current_location = (existing.get("warehouseLocation") or "").strip()
                already_correct = (
                    current_name == name
                    and current_location == WAREHOUSE_LOCATION
                )

                if already_correct:
                    # Nothing to do — skip the PUT to conserve API quota
                    print(f"{sku:<{col_sku}}{'already set':<{col_action}}{str(product_id):<{col_id}}✅ (no change needed)")
                    results.append(_product_result(
                        sku, "already-set", existing, product_id, True, name
                    ))
                else:
                    action_label = "would-update" if dry_run else "updated"
                    if not dry_run:
                        update_product(product_id, existing, name, headers)
                        existing = verify_product_configuration(
                            find_product_by_sku(sku, headers), sku, name
                        )
                    icon = "✅" if not dry_run else "—"
                    print(f"{sku:<{col_sku}}{action_label:<{col_action}}{str(product_id):<{col_id}}{icon}")
                    results.append(_product_result(
                        sku, action_label, existing, product_id, True, name
                    ))

            else:
                # ── Product missing — create via placeholder order ──
                if dry_run:
                    print(f"{sku:<{col_sku}}{'would-create':<{col_action}}{'—':<{col_id}}— (placeholder order → product)")
                    results.append(_product_result(
                        sku, "would-create", None, None, True, name
                    ))
                    continue

                order_id = None
                try:
                    # Step 1: create placeholder order (generates the product record)
                    order_id = create_placeholder_order(sku, name, headers)
                    time.sleep(2.0)  # give ShipStation a moment to ingest the order

                    # Step 2: find the newly-created product
                    product = find_product_by_sku(sku, headers)

                    if not product:
                        # Retry once after a longer wait
                        time.sleep(5.0)
                        product = find_product_by_sku(sku, headers)

                    if not product:
                        raise RuntimeError(
                            "product record not found after placeholder order was created"
                        )

                    product_id = product.get("productId", "?")

                    # Step 3: update required name and warehouse location, then verify
                    update_product(product_id, product, name, headers)
                    product = verify_product_configuration(
                        find_product_by_sku(sku, headers), sku, name
                    )
                finally:
                    if order_id is not None:
                        try:
                            delete_order(order_id, headers)
                        except Exception as cleanup_error:
                            if sys.exc_info()[0] is None:
                                raise
                            print(
                                f"    (warning: placeholder cleanup failed while preserving "
                                f"the original error: {cleanup_error})"
                            )

                print(f"{sku:<{col_sku}}{'created':<{col_action}}{str(product_id):<{col_id}}✅")
                results.append(_product_result(
                    sku, "created", product, product_id, True, name
                ))

        except Exception as exc:
            print(f"{sku:<{col_sku}}{'ERROR':<{col_action}}{'—':<{col_id}}❌ {exc}")
            results.append(_product_result(
                sku, "error", None, None, False, name, str(exc)
            ))

    print("-" * 80)
    ok_count  = sum(1 for r in results if r["ok"])
    err_count = sum(1 for r in results if not r["ok"])
    label = "DRY RUN complete" if dry_run else "Done"
    print(f"\n{label}: {ok_count} succeeded, {err_count} failed out of {len(results)} SKUs")
    _write_report(args.report, results, dry_run)

    if err_count:
        sys.exit(1)


if __name__ == "__main__":
    main()
