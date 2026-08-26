import contextlib
import datetime

import pandas as pd

from src.services.reporting_logic.average_calculations import (
    calculate_12_month_rolling_average,
)
from src.services.reporting_logic.week_utils import (
    get_rolling_week_boundaries,
    iter_rolling_weeks,
)


def test_wednesday_window_uses_prior_complete_week():
    assert get_rolling_week_boundaries(
        as_of_date=datetime.date(2026, 8, 26)
    ) == (datetime.date(2025, 8, 25), datetime.date(2026, 8, 23))


def test_friday_window_includes_current_business_complete_week():
    assert get_rolling_week_boundaries(
        as_of_date=datetime.date(2026, 8, 28)
    ) == (datetime.date(2025, 9, 1), datetime.date(2026, 8, 30))


def test_average_uses_fixed_denominator_for_missing_zero_weeks():
    frame = pd.DataFrame(
        [
            {"Date": "2026-08-10", "SKU": "17612", "ShippedQuantity": 520},
            {"Date": "2026-08-17", "SKU": "17612", "ShippedQuantity": 520},
        ]
    )

    result = calculate_12_month_rolling_average(
        frame, as_of_date=datetime.date(2026, 8, 26)
    )

    assert result.set_index("SKU").loc["17612", "12-Month Rolling Average"] == 20


def test_average_ignores_rows_outside_exact_52_week_window():
    weeks = iter_rolling_weeks(as_of_date=datetime.date(2026, 8, 26))
    rows = [
        {"Date": start, "SKU": "17612", "ShippedQuantity": 10}
        for start, _ in weeks
    ]
    rows.extend(
        [
            {
                "Date": weeks[0][0] - datetime.timedelta(days=7),
                "SKU": "17612",
                "ShippedQuantity": 9999,
            },
            {
                "Date": weeks[-1][0] + datetime.timedelta(days=7),
                "SKU": "17612",
                "ShippedQuantity": 9999,
            },
        ]
    )

    result = calculate_12_month_rolling_average(
        pd.DataFrame(rows), as_of_date=datetime.date(2026, 8, 26)
    )

    assert result.set_index("SKU").loc["17612", "12-Month Rolling Average"] == 10


def test_backfill_writes_full_window_with_zero_and_resolved_quantities(monkeypatch):
    import src.daily_shipment_processor as processor

    target_skus = ["17612", "17904", "17914", "18675", "18795"]
    query_calls = []
    writes = []

    def fake_execute_query(query, params=None):
        query_calls.append((query, params))
        if "FROM sku_promotions" in query:
            return [("PROMO-17612", "17612")]
        if "FROM sku_variants" in query:
            return [("18675-6", "18675", 6)]
        return [
            (datetime.date(2026, 4, 6), "ORDER-1", "17612", "PROMO-17612", 120),
            (datetime.date(2026, 4, 6), "ORDER-2", "18675", "18675-6", 3),
        ]

    class FakeCursor:
        def execute(self, query, params=None):
            writes.append((query, params))

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

    @contextlib.contextmanager
    def fake_transaction():
        yield FakeConnection()

    monkeypatch.setattr(processor, "execute_query", fake_execute_query)
    monkeypatch.setattr(processor, "transaction", fake_transaction)

    result = processor.backfill_weekly_history_from_shipped_items(
        target_skus=target_skus,
        as_of_date=datetime.date(2026, 8, 26),
    )

    assert result["weeks_processed"] == 52
    assert result["records_updated"] == 52 * len(target_skus)
    assert len(writes) == 52 * len(target_skus)

    assert any("FROM sku_promotions" in query for query, _ in query_calls)
    assert any("FROM sku_variants" in query for query, _ in query_calls)

    quantities = {
        (params[0], params[2]): params[3]
        for _, params in writes
    }
    assert quantities[("2026-04-06", "17612")] == 120
    assert quantities[("2026-04-06", "18675")] == 18
    assert quantities[("2026-04-06", "17904")] == 0


def test_backfill_fails_if_active_sku_maps_cannot_be_loaded(monkeypatch):
    import src.daily_shipment_processor as processor

    @contextlib.contextmanager
    def transaction_must_not_start():
        raise AssertionError("backfill must stop before writing")
        yield

    def fake_execute_query(query, params=None):
        if "FROM shipped_items" in query:
            return []
        raise RuntimeError("mapping tables unavailable")

    monkeypatch.setattr(processor, "execute_query", fake_execute_query)
    monkeypatch.setattr(processor, "transaction", transaction_must_not_start)

    try:
        processor.backfill_weekly_history_from_shipped_items(
            target_skus=["17612"],
            as_of_date=datetime.date(2026, 8, 26),
        )
    except RuntimeError as exc:
        assert "mapping tables unavailable" in str(exc)
    else:
        raise AssertionError("mapping failure must abort reconciliation")


def test_historical_variant_uses_raw_sku_lot_and_ignores_stale_duplicate():
    import src.daily_shipment_processor as processor

    rows = [
        ("ORDER-1", "17612", "17612-6", 1),
        ("ORDER-1", "17612", "17612 - LOT-001", 6),
        ("ORDER-2", "17612", "17612-6", 2),
    ]
    variant_map = {
        "17612-6": {"base_sku": "17612", "unit_multiplier": 6}
    }

    totals = processor._resolve_shipped_totals(
        rows, promo_map={}, variant_map=variant_map
    )

    assert totals == {"17612": 18}


def test_daily_writer_persists_variant_as_canonical_six_units(monkeypatch):
    import src.daily_shipment_processor as processor

    writes = []

    class FakeConnection:
        pass

    @contextlib.contextmanager
    def fake_transaction():
        yield FakeConnection()

    def fake_upsert(conn, **kwargs):
        writes.append(kwargs)

    frame = pd.DataFrame(
        [{
            "Ship Date": datetime.date(2026, 8, 17),
            "SKU - Lot": "17612-6",
            "Base SKU": "17612",
            "Quantity Shipped": 1,
            "OrderNumber": "ORDER-1",
            "TrackingNumber": "TRACK-1",
        }]
    )
    monkeypatch.setattr(processor, "transaction", fake_transaction)
    monkeypatch.setattr(processor, "upsert_shipped_item", fake_upsert)

    saved = processor.save_shipped_items_to_db(
        frame,
        promo_map={},
        variant_map={
            "17612-6": {"base_sku": "17612", "unit_multiplier": 6}
        },
    )

    assert saved == 1
    assert writes[0]["base_sku"] == "17612"
    assert writes[0]["sku_lot"] == "17612"
    assert writes[0]["quantity"] == 6