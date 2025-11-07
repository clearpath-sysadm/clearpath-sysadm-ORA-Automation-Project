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
from typing import Tuple


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


def get_current_week_boundaries() -> Tuple[datetime.date, datetime.date]:
    """
    Get the Monday-Sunday boundaries for the current week.
    
    Returns:
        Tuple of (monday_start, sunday_end) for the current week
    """
    today = datetime.date.today()
    return get_week_boundaries(today)


def is_week_complete(week_end_date: datetime.date) -> bool:
    """
    Determine if a week is complete for reporting purposes.
    
    BUSINESS RULE: Friday is the last shipping day. A week is considered complete
    on Friday or later, even though the calendar week runs Monday-Sunday.
    
    Args:
        week_end_date: The end date of the week (should be a Sunday)
        
    Returns:
        True if the week is complete (Friday or later), False otherwise
    """
    today = datetime.date.today()
    
    # Calculate Friday of that week (week_end_date is Sunday, so Friday is -2 days)
    friday_of_week = week_end_date - datetime.timedelta(days=2)
    
    # Week is complete if today is Friday or later (includes Friday, Saturday, Sunday)
    return today >= friday_of_week


def get_prior_complete_week_boundaries() -> Tuple[datetime.date, datetime.date]:
    """
    Get the boundaries of the most recent COMPLETE week (the week before the current week).
    
    Returns:
        Tuple of (monday_start, sunday_end) for the prior complete week
    """
    current_monday, current_sunday = get_current_week_boundaries()
    
    # Go back 7 days from current Monday to get prior week's Monday
    prior_monday = current_monday - datetime.timedelta(days=7)
    prior_sunday = prior_monday + datetime.timedelta(days=6)
    
    return prior_monday, prior_sunday
