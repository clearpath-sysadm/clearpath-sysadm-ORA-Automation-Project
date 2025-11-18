#!/usr/bin/env python3
"""
Business Hours Utility
Centralized business hours checking for all automation workflows.

BUSINESS HOURS:
- Monday - Friday: 6 AM - 6 PM Central Time (CST/CDT)
- Saturday: OFF
- Sunday: OFF

Purpose: Reduce database compute time by sleeping workflows during non-business hours.
Database billing: Active when receiving requests + 5 min after last request.
By sleeping overnight/weekends, database becomes inactive and billing pauses.

Expected savings: 64% reduction in database compute time
(168 hrs/week → 60 hrs/week)
"""

import datetime
import pytz
import logging

logger = logging.getLogger(__name__)

BUSINESS_START_HOUR = 6   # 6 AM CST
BUSINESS_END_HOUR = 18    # 6 PM CST (18:00 in 24-hour format)
TIMEZONE = 'America/Chicago'  # Central Time


def is_business_hours() -> bool:
    """
    Check if current time is within business hours.
    
    Business hours:
    - Monday - Friday: 6 AM - 6 PM Central Time
    - Saturday: OFF
    - Sunday: OFF
    
    Returns:
        bool: True if within business hours, False otherwise
    """
    try:
        central = pytz.timezone(TIMEZONE)
        now = datetime.datetime.now(central)
        
        # Check if weekend (Saturday=5, Sunday=6)
        if now.weekday() >= 5:
            return False
        
        # Check if within business hours (6 AM - 6 PM)
        # Hour 18 means 6:00 PM - 6:59 PM, so we exclude it (>= 18)
        if now.hour < BUSINESS_START_HOUR or now.hour >= BUSINESS_END_HOUR:
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking business hours: {e}")
        # Fail-open: allow workflow to run if check fails
        return True


def get_sleep_until_business_hours() -> int:
    """
    Calculate seconds to sleep until next business hours period.
    
    Returns:
        int: Seconds to sleep (minimum 60, maximum 3600)
    """
    try:
        central = pytz.timezone(TIMEZONE)
        now = datetime.datetime.now(central)
        
        # If weekend, sleep until Monday 6 AM
        if now.weekday() >= 5:  # Saturday or Sunday
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            next_business_day = now + datetime.timedelta(days=days_until_monday)
            next_start = next_business_day.replace(hour=BUSINESS_START_HOUR, minute=0, second=0, microsecond=0)
            seconds = int((next_start - now).total_seconds())
            # Cap at 1 hour to allow periodic health checks
            return min(seconds, 3600)
        
        # If before 6 AM, sleep until 6 AM today
        if now.hour < BUSINESS_START_HOUR:
            next_start = now.replace(hour=BUSINESS_START_HOUR, minute=0, second=0, microsecond=0)
            seconds = int((next_start - now).total_seconds())
            return min(seconds, 3600)
        
        # If after 6 PM, sleep until 6 AM tomorrow
        if now.hour >= BUSINESS_END_HOUR:
            # Check if tomorrow is weekend
            tomorrow = now + datetime.timedelta(days=1)
            if tomorrow.weekday() >= 5:  # Tomorrow is Saturday/Sunday
                days_until_monday = (7 - tomorrow.weekday()) % 7
                if days_until_monday == 0:
                    days_until_monday = 1
                next_business_day = tomorrow + datetime.timedelta(days=days_until_monday - 1)
                next_start = next_business_day.replace(hour=BUSINESS_START_HOUR, minute=0, second=0, microsecond=0)
            else:
                next_start = tomorrow.replace(hour=BUSINESS_START_HOUR, minute=0, second=0, microsecond=0)
            
            seconds = int((next_start - now).total_seconds())
            return min(seconds, 3600)
        
        # Default: sleep 1 hour
        return 3600
        
    except Exception as e:
        logger.error(f"Error calculating sleep time: {e}")
        return 3600  # Default to 1 hour


def format_business_hours_status() -> str:
    """
    Get human-readable business hours status.
    
    Returns:
        str: Status message with current time and business hours state
    """
    try:
        central = pytz.timezone(TIMEZONE)
        now = datetime.datetime.now(central)
        
        day_name = now.strftime('%A')
        current_time = now.strftime('%I:%M %p CST')
        
        if is_business_hours():
            return f"✅ BUSINESS HOURS | {day_name} {current_time} | Active"
        else:
            if now.weekday() >= 5:
                return f"⏰ WEEKEND | {day_name} {current_time} | Sleeping"
            elif now.hour < BUSINESS_START_HOUR:
                return f"⏰ BEFORE HOURS | {day_name} {current_time} | Sleeping (starts 6 AM)"
            else:
                return f"⏰ AFTER HOURS | {day_name} {current_time} | Sleeping (ended 6 PM)"
    
    except Exception as e:
        return f"⚠️ Error getting status: {e}"


if __name__ == '__main__':
    # Test the business hours logic
    print("Business Hours Utility - Test Mode")
    print("=" * 60)
    print(f"Current Status: {format_business_hours_status()}")
    print(f"Is Business Hours: {is_business_hours()}")
    print(f"Sleep Duration: {get_sleep_until_business_hours()} seconds")
    print("=" * 60)
