"""
Week Utilities for Rolling Average Calculations

Provides functions to calculate week boundaries and determine complete vs partial weeks.

BUSINESS RULES:
- Calendar weeks run Monday (start) to Sunday (end)
- Shipping only occurs Monday through Friday
- Friday is the last shipping day of the week
- Weekly inventory reports are sent on Friday
- A week is considered "complete" for reporting once Friday has passed
"""

import datetime
from typing import List, Optional, Tuple


ROLLING_WEEKS = 52


def get_week_boundaries(date: datetime.date) -> Tuple[datetime.date, datetime.date]:
    """
    Get the Monday-Sunday boundaries for the week containing the given date.
    
    Args:
        date: Any date within the week
        
    Returns:
        Tuple of (monday_start, sunday_end) for that week
    """
    # weekday() returns 0=Monday, 6=Sunday
    days_since_monday = date.weekday()
    monday_start = date - datetime.timedelta(days=days_since_monday)
    sunday_end = monday_start + datetime.timedelta(days=6)
    
    return monday_start, sunday_end


def get_current_week_boundaries(
    as_of_date: Optional[datetime.date] = None,
) -> Tuple[datetime.date, datetime.date]:
    """
    Get the Monday-Sunday boundaries for the current week.
    
    Returns:
        Tuple of (monday_start, sunday_end) for the current week
    """
    today = as_of_date or datetime.date.today()
    return get_week_boundaries(today)


def is_week_complete(
    week_end_date: datetime.date,
    as_of_date: Optional[datetime.date] = None,
) -> bool:
    """
    Determine if a week is complete for reporting purposes.
    
    BUSINESS RULE: Friday is the last shipping day. A week is considered complete
    on Friday or later, even though the calendar week runs Monday-Sunday.
    
    Args:
        week_end_date: The end date of the week (should be a Sunday)
        
    Returns:
        True if the week is complete (Friday or later), False otherwise
    """
    today = as_of_date or datetime.date.today()
    
    # Calculate Friday of that week (week_end_date is Sunday, so Friday is -2 days)
    friday_of_week = week_end_date - datetime.timedelta(days=2)
    
    # Week is complete if today is Friday or later (includes Friday, Saturday, Sunday)
    return today >= friday_of_week


def get_prior_complete_week_boundaries(
    as_of_date: Optional[datetime.date] = None,
) -> Tuple[datetime.date, datetime.date]:
    """
    Get the boundaries of the most recent COMPLETE week (the week before the current week).
    
    Returns:
        Tuple of (monday_start, sunday_end) for the prior complete week
    """
    current_monday, current_sunday = get_current_week_boundaries(as_of_date)
    
    # Go back 7 days from current Monday to get prior week's Monday
    prior_monday = current_monday - datetime.timedelta(days=7)
    prior_sunday = prior_monday + datetime.timedelta(days=6)
    
    return prior_monday, prior_sunday


def get_latest_complete_week_boundaries(
    as_of_date: Optional[datetime.date] = None,
) -> Tuple[datetime.date, datetime.date]:
    """
    Return the Monday-Sunday boundaries for the latest business-complete week.

    Friday is the final shipping day, so the current calendar week is complete
    on Friday, Saturday, and Sunday. Earlier in the week, the latest complete
    week is the prior Monday-Sunday period.
    """
    today = as_of_date or datetime.date.today()
    current_monday, current_sunday = get_current_week_boundaries(today)
    if is_week_complete(current_sunday, today):
        return current_monday, current_sunday
    return get_prior_complete_week_boundaries(today)


def get_rolling_week_boundaries(
    weeks: int = ROLLING_WEEKS,
    as_of_date: Optional[datetime.date] = None,
) -> Tuple[datetime.date, datetime.date]:
    """Return the inclusive boundaries of the latest ``weeks`` complete weeks."""
    if weeks < 1:
        raise ValueError("weeks must be at least 1")

    latest_monday, latest_sunday = get_latest_complete_week_boundaries(as_of_date)
    earliest_monday = latest_monday - datetime.timedelta(weeks=weeks - 1)
    return earliest_monday, latest_sunday


def iter_rolling_weeks(
    weeks: int = ROLLING_WEEKS,
    as_of_date: Optional[datetime.date] = None,
) -> List[Tuple[datetime.date, datetime.date]]:
    """Return each Monday-Sunday pair in the rolling window, oldest first."""
    first_monday, _ = get_rolling_week_boundaries(weeks, as_of_date)
    return [
        (
            first_monday + datetime.timedelta(weeks=offset),
            first_monday + datetime.timedelta(weeks=offset, days=6),
        )
        for offset in range(weeks)
    ]
