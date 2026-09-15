"""Focused tests for Auto Ship Day and durable FedEx reminder behavior."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.services.operational_reminders import (
    auto_ship_status,
    get_fedex_status,
    mark_fedex_reminder_completed,
    record_fedex_threshold,
)


def utc(year, month, day, hour=12, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def test_auto_ship_days_are_server_defined_in_central_time():
    for day in (5, 15, 25):
        status = auto_ship_status(utc(2026, 9, day, 18))
        assert status['is_auto_ship_day'] is True
        assert status['day_of_month'] == day

    assert auto_ship_status(utc(2026, 9, 16, 18))['is_auto_ship_day'] is False


def test_auto_ship_weekend_details_are_returned_for_frontend_copy():
    # September 5, 2026 is a Saturday.
    status = auto_ship_status(utc(2026, 9, 5, 18))
    assert status['is_auto_ship_day'] is True
    assert status['is_weekend'] is True
    assert status['day_name'] == 'Saturday'


def test_central_midnight_controls_the_operational_date():
    before_midnight = auto_ship_status(utc(2026, 9, 15, 4, 59))
    after_midnight = auto_ship_status(utc(2026, 9, 15, 5, 1))

    assert before_midnight['operational_date'] == '2026-09-14'
    assert before_midnight['is_auto_ship_day'] is False
    assert after_midnight['operational_date'] == '2026-09-15'
    assert after_midnight['is_auto_ship_day'] is True


def test_threshold_is_latched_only_at_185_or_more():
    conn = MagicMock()
    cursor = conn.cursor.return_value

    assert record_fedex_threshold(conn, 184, utc(2026, 9, 15)) is False
    cursor.execute.assert_not_called()

    assert record_fedex_threshold(conn, 185, utc(2026, 9, 15)) is True
    args = cursor.execute.call_args.args[1]
    assert str(args[0]) == '2026-09-15'
    assert args[1] == 185


def test_latched_reminder_stays_needed_after_live_count_drops():
    conn = MagicMock()
    select_cursor = MagicMock()
    select_cursor.fetchone.return_value = (
        231,
        datetime(2026, 9, 15, 14, tzinfo=timezone.utc),
        None,
        None,
    )
    conn.cursor.return_value = select_cursor

    status = get_fedex_status(conn, 0, utc(2026, 9, 15, 20))

    assert status == {
        'needed': True,
        'completed': False,
        'completed_at': None,
        'peak_units': 231,
    }


def test_completed_reminder_closes_pending_state():
    completed_at = datetime(2026, 9, 15, 20, tzinfo=timezone.utc)
    conn = MagicMock()
    select_cursor = MagicMock()
    select_cursor.fetchone.return_value = (
        231,
        datetime(2026, 9, 15, 14, tzinfo=timezone.utc),
        completed_at,
        completed_at,
    )
    conn.cursor.return_value = select_cursor

    status = get_fedex_status(conn, 0, utc(2026, 9, 15, 21))

    assert status['needed'] is False
    assert status['completed'] is True
    assert status['completed_at'] == completed_at


def test_legacy_naive_completion_timestamp_is_returned_as_utc():
    completed_at = datetime(2026, 9, 15, 20)
    conn = MagicMock()
    select_cursor = MagicMock()
    select_cursor.fetchone.return_value = (
        231,
        datetime(2026, 9, 15, 14),
        None,
        completed_at,
    )
    conn.cursor.return_value = select_cursor

    status = get_fedex_status(conn, 0, utc(2026, 9, 15, 21))

    assert status['needed'] is False
    assert status['completed_at'].isoformat().endswith('+00:00')


def test_next_day_without_threshold_has_no_reminder():
    conn = MagicMock()
    select_cursor = MagicMock()
    select_cursor.fetchone.return_value = None
    conn.cursor.return_value = select_cursor

    status = get_fedex_status(conn, 0, utc(2026, 9, 16, 18))

    assert status['needed'] is False
    assert status['completed'] is False


def test_mark_complete_uses_the_central_operational_date():
    completed_at = datetime(2026, 9, 15, 5, 30, tzinfo=timezone.utc)
    conn = MagicMock()
    cursor = conn.cursor.return_value

    mark_fedex_reminder_completed(conn, completed_at, completed_at)

    params = cursor.execute.call_args.args[1]
    assert params[0] == completed_at
    assert str(params[1]) == '2026-09-15'


def test_dashboard_no_longer_uses_browser_date_for_auto_ship():
    html = open('index.html', encoding='utf-8').read()
    assert 'data.auto_ship' in html
    assert 'autoShipDays.includes' not in html
    assert 'checkAutoShipDay()' not in html
