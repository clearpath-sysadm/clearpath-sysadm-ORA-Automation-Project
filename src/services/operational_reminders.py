"""Central-Time operational reminder state shared by dashboard and workers."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


CENTRAL_TIME = ZoneInfo("America/Chicago")
AUTO_SHIP_DAYS = frozenset({5, 15, 25})
FEDEX_PICKUP_THRESHOLD = 185


def central_now(now=None):
    """Return an aware America/Chicago datetime for an optional instant."""
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(CENTRAL_TIME)


def auto_ship_status(now=None):
    """Build the server-authoritative Auto Ship Day display state."""
    current = central_now(now)
    day = current.day
    weekday = current.weekday()  # Monday=0, Sunday=6
    return {
        "operational_date": current.date().isoformat(),
        "is_auto_ship_day": day in AUTO_SHIP_DAYS,
        "day_of_month": day,
        "day_name": current.strftime("%A"),
        "is_weekend": weekday >= 5,
    }


def record_fedex_threshold(conn, units_to_ship, now=None):
    """Latch today's FedEx reminder once the unit threshold is reached."""
    units = int(units_to_ship or 0)
    if units < FEDEX_PICKUP_THRESHOLD:
        return False

    operational_date = central_now(now).date()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO fedex_pickup_reminder_state
                (operational_date, peak_units, threshold_reached_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (operational_date) DO UPDATE
                SET peak_units = GREATEST(
                    fedex_pickup_reminder_state.peak_units,
                    EXCLUDED.peak_units
                )
            """,
            (operational_date, units),
        )
    finally:
        cursor.close()
    return True


def get_fedex_status(conn, units_to_ship, now=None):
    """Return today's durable FedEx reminder/completion state."""
    current = central_now(now)
    operational_date = current.date()
    record_fedex_threshold(conn, units_to_ship, now=current)

    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT
                state.peak_units,
                state.threshold_reached_at,
                state.completed_at,
                log.completed_at
            FROM fedex_pickup_reminder_state state
            LEFT JOIN LATERAL (
                SELECT completed_at
                FROM fedex_pickup_log
                WHERE pickup_date = state.operational_date
                ORDER BY completed_at DESC
                LIMIT 1
            ) log ON TRUE
            WHERE state.operational_date = %s
            """,
            (operational_date,),
        )
        row = cursor.fetchone()
    finally:
        cursor.close()

    if not row:
        return {
            "needed": False,
            "completed": False,
            "completed_at": None,
            "peak_units": 0,
        }

    peak_units, _threshold_reached_at, state_completed_at, log_completed_at = row
    completed_at = state_completed_at or log_completed_at
    if completed_at is not None and completed_at.tzinfo is None:
        # Legacy fedex_pickup_log.completed_at is timestamp without time zone.
        # PostgreSQL CURRENT_TIMESTAMP was stored in UTC in this application.
        completed_at = completed_at.replace(tzinfo=timezone.utc)
    return {
        "needed": completed_at is None,
        "completed": completed_at is not None,
        "completed_at": completed_at,
        "peak_units": peak_units,
    }


def mark_fedex_reminder_completed(conn, completed_at, now=None):
    """Close today's latched reminder in the same transaction as its audit log."""
    operational_date = central_now(now).date()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE fedex_pickup_reminder_state
            SET completed_at = %s
            WHERE operational_date = %s
            """,
            (completed_at, operational_date),
        )
    finally:
        cursor.close()
