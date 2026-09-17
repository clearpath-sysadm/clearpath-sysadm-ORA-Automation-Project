"""Build the live pick summary from ShipStation awaiting-shipment orders."""

from collections import defaultdict

from src.services.data_processing.sku_lot_parser import parse_cf1
from src.services.inventory.promo_sku_utils import resolve_sku_and_quantity


EXPEDITED_SERVICE_CODES = {
    "fedex_2day",
    "fedex_standard_overnight",
    "ups_2nd_day_air",
}


def _item_sku_and_lot(raw_sku):
    raw_sku = str(raw_sku or "").strip()
    if " - " in raw_sku:
        return raw_sku.split(" - ", 1)[0].strip(), raw_sku
    return raw_sku, None


def _order_lot_stamp(order):
    advanced = order.get("advancedOptions") or {}
    return str(advanced.get("customField1") or "").strip()


def build_live_shipment_summary(orders, promo_map, variant_map, product_names):
    """Aggregate approved products after resolving configured variants and promos."""
    grouped = defaultdict(int)
    benco_units = 0
    expedited_units = 0

    for order in orders:
        ship_to = order.get("shipTo") or {}
        company = str(ship_to.get("company") or "").upper()
        is_benco = "BENCO" in company
        is_expedited = order.get("serviceCode") in EXPEDITED_SERVICE_CODES
        cf1 = _order_lot_stamp(order)
        parsed_cf1 = parse_cf1(cf1)

        for item in order.get("items") or []:
            raw_base, item_lot = _item_sku_and_lot(item.get("sku"))
            quantity = int(item.get("quantity") or 0)
            if not raw_base or quantity <= 0:
                continue

            base_sku, effective_quantity = resolve_sku_and_quantity(
                raw_base, quantity, promo_map, variant_map
            )
            if base_sku not in product_names:
                continue

            if item_lot and " - " in item_lot:
                lot_number = item_lot.split(" - ", 1)[1].strip()
                item_lot = f"{base_sku} - {lot_number}"
            if (
                item_lot is None
                and parsed_cf1
                and parsed_cf1[0] == base_sku
            ):
                item_lot = cf1

            grouped[(base_sku, item_lot)] += effective_quantity
            if is_benco:
                benco_units += effective_quantity
            if is_expedited:
                expedited_units += effective_quantity

    by_sku = {}
    grand_total = 0

    for (sku, sku_lot), units in sorted(
        grouped.items(), key=lambda row: (row[0][0], row[0][1] or "")
    ):
        grand_total += units
        if sku not in by_sku:
            by_sku[sku] = {
                "base_sku": sku,
                "product_name": product_names[sku],
                "lots": [],
                "total_units": 0,
            }

        lot_number = None
        if sku_lot and " - " in sku_lot:
            lot_number = sku_lot.split(" - ", 1)[1].strip()
        elif sku_lot:
            lot_number = sku_lot

        by_sku[sku]["total_units"] += units
        by_sku[sku]["lots"].append(
            {
                "sku_lot": sku_lot,
                "lot_number": lot_number,
                "units": units,
                "is_end_of_lot": False,
            }
        )

    for entry in by_sku.values():
        assigned_lots = [lot for lot in entry["lots"] if lot["lot_number"]]
        if len(assigned_lots) > 1:
            assigned_lots[0]["is_end_of_lot"] = True

    return {
        "rows": sorted(by_sku.values(), key=lambda row: row["base_sku"]),
        "grand_total": grand_total,
        "benco_units": benco_units,
        "expedited_units": expedited_units,
    }