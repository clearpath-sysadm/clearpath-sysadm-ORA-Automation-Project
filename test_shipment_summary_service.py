from src.services.reporting_logic.shipment_summary_service import (
    build_live_shipment_summary,
)


PROMOS = {
    "17613": "17612",
    "17905": "17904",
    "17915": "17914",
    "18676": "18675",
}

VARIANTS = {
    f"{base}-{size}": {
        "base_sku": base,
        "unit_multiplier": size,
    }
    for base in ("17612", "17904", "17914", "18675")
    for size in (1, 6, 15, 40)
}

NAMES = {
    "17612": "PT Kit",
    "17904": "Travel Kit",
    "17914": "PPR Kit",
    "18675": "OraCare Toothbrush",
    "18795": "OraPro Paste Peppermint",
}


def order(*items, cf1="", company="", service_code=""):
    return {
        "items": [
            {"sku": sku, "quantity": quantity}
            for sku, quantity in items
        ],
        "advancedOptions": {"customField1": cf1},
        "shipTo": {"company": company},
        "serviceCode": service_code,
    }


def totals(summary):
    return {row["base_sku"]: row["total_units"] for row in summary["rows"]}


def test_resolves_every_variant_and_promo_family_into_base_units():
    orders = [
        order(("17612-1", 100), ("17612-15", 2), ("17612-6", 6), ("17613", 23)),
        order(("17904-6", 2), ("17905", 3)),
        order(("17914-15", 2), ("17915", 4)),
        order(("18675-40", 1), ("18676", 5)),
        order(("18795", 7)),
    ]

    summary = build_live_shipment_summary(orders, PROMOS, VARIANTS, NAMES)

    assert totals(summary) == {
        "17612": 189,
        "17904": 15,
        "17914": 34,
        "18675": 45,
        "18795": 7,
    }
    assert summary["grand_total"] == 290


def test_groups_resolved_units_by_matching_item_or_order_lot():
    orders = [
        order(("17612-6", 2), cf1="17612 - 260228"),
        order(("17613 - 260228", 3)),
        order(("17612-1", 1), cf1="17904 - 260125"),
    ]

    summary = build_live_shipment_summary(orders, PROMOS, VARIANTS, NAMES)
    pt = next(row for row in summary["rows"] if row["base_sku"] == "17612")

    assert pt["total_units"] == 16
    assert {(lot["lot_number"], lot["units"]) for lot in pt["lots"]} == {
        (None, 1),
        ("260228", 15),
    }


def test_subtotals_use_effective_units_not_raw_line_quantities():
    orders = [
        order(("17612-15", 2), company="BENCO Dental"),
        order(("17904-6", 3), service_code="fedex_2day"),
    ]

    summary = build_live_shipment_summary(orders, PROMOS, VARIANTS, NAMES)

    assert summary["benco_units"] == 30
    assert summary["expedited_units"] == 18


def test_excludes_unapproved_base_variant_and_promo_like_skus_from_all_totals():
    orders = [
        order(
            ("17612", 2),
            ("17811-EN-100", 10),
            ("18565-25", 20),
            ("18684", 30),
            company="BENCO Dental",
            service_code="fedex_2day",
        ),
    ]

    summary = build_live_shipment_summary(orders, PROMOS, VARIANTS, NAMES)

    assert totals(summary) == {"17612": 2}
    assert summary["grand_total"] == 2
    assert summary["benco_units"] == 2
    assert summary["expedited_units"] == 2
    assert "unresolved_skus" not in summary


def test_excludes_configured_mapping_when_resolved_base_is_not_approved():
    promos = {**PROMOS, "99998": "99999"}
    variants = {
        **VARIANTS,
        "88888-6": {"base_sku": "88888", "unit_multiplier": 6},
    }
    orders = [order(("99998", 4), ("88888-6", 3))]

    summary = build_live_shipment_summary(orders, promos, variants, NAMES)

    assert summary["rows"] == []
    assert summary["grand_total"] == 0
    assert summary["benco_units"] == 0
    assert summary["expedited_units"] == 0