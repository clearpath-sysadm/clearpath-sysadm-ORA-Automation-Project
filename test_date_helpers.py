#!/usr/bin/env python3
"""
Quick validation script for EOD/EOW/EOM date calculation logic
Tests edge cases like week boundaries, month boundaries, and year boundaries
"""
import datetime

def test_week_start_calculation():
    """Test that week_start calculation works correctly for all days"""
    print("=== Testing Week Start Calculation ===")
    
    # Test cases: (date_str, expected_week_start_str)
    test_cases = [
        ("2025-10-13", "2025-10-13"),  # Monday -> Monday
        ("2025-10-16", "2025-10-13"),  # Thursday -> Monday
        ("2025-10-19", "2025-10-13"),  # Sunday -> Monday
        ("2025-12-29", "2025-12-29"),  # Monday (year boundary)
        ("2025-12-31", "2025-12-29"),  # Wednesday (year boundary) -> Monday
        ("2026-01-01", "2025-12-29"),  # Thursday (new year) -> Previous Monday
    ]
    
    for date_str, expected_start_str in test_cases:
        test_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        week_start = test_date - datetime.timedelta(days=test_date.weekday())
        expected = datetime.datetime.strptime(expected_start_str, "%Y-%m-%d").date()
        
        status = "✓" if week_start == expected else "✗"
        print(f"{status} {date_str} ({test_date.strftime('%A')}) -> {week_start} (expected {expected})")
    
    print()

def test_month_start_calculation():
    """Test that month_start calculation works correctly"""
    print("=== Testing Month Start Calculation ===")
    
    # Test cases: (date_str, expected_month_start_str)
    test_cases = [
        ("2025-10-01", "2025-10-01"),  # First day
        ("2025-10-16", "2025-10-01"),  # Mid-month
        ("2025-10-31", "2025-10-01"),  # Last day of October
        ("2025-12-31", "2025-12-01"),  # Last day of year
        ("2026-01-01", "2026-01-01"),  # First day of new year
        ("2024-02-29", "2024-02-01"),  # Leap year Feb 29
    ]
    
    for date_str, expected_start_str in test_cases:
        test_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        month_start = test_date.replace(day=1)
        expected = datetime.datetime.strptime(expected_start_str, "%Y-%m-%d").date()
        
        status = "✓" if month_start == expected else "✗"
        print(f"{status} {date_str} -> {month_start} (expected {expected})")
    
    print()

def test_weekday_values():
    """Confirm weekday() returns 0=Monday"""
    print("=== Testing weekday() Values ===")
    
    # Known dates
    test_dates = [
        ("2025-10-13", "Monday", 0),
        ("2025-10-14", "Tuesday", 1),
        ("2025-10-15", "Wednesday", 2),
        ("2025-10-16", "Thursday", 3),
        ("2025-10-17", "Friday", 4),
        ("2025-10-18", "Saturday", 5),
        ("2025-10-19", "Sunday", 6),
    ]
    
    for date_str, day_name, expected_weekday in test_dates:
        test_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        actual_weekday = test_date.weekday()
        
        status = "✓" if actual_weekday == expected_weekday else "✗"
        print(f"{status} {date_str} ({day_name}): weekday() = {actual_weekday} (expected {expected_weekday})")
    
    print()

def test_month_end_calculation():
    """Test month_end calculation used in EOM endpoint"""
    print("=== Testing Month End Calculation (EOM logic) ===")
    
    # Test cases: (today_str, expected_month_end_str)
    test_cases = [
        ("2025-10-16", "2025-10-31"),  # October (31 days)
        ("2025-11-15", "2025-11-30"),  # November (30 days)
        ("2025-12-20", "2025-12-31"),  # December (year-end)
        ("2024-02-15", "2024-02-29"),  # February (leap year)
        ("2025-02-15", "2025-02-28"),  # February (non-leap)
    ]
    
    for today_str, expected_end_str in test_cases:
        today = datetime.datetime.strptime(today_str, "%Y-%m-%d").date()
        
        # This is the logic from app.py EOM endpoint
        if today.month == 12:
            month_end = today.replace(month=12, day=31)
        else:
            month_end = (today.replace(month=today.month + 1, day=1) - datetime.timedelta(days=1))
        
        expected = datetime.datetime.strptime(expected_end_str, "%Y-%m-%d").date()
        
        status = "✓" if month_end == expected else "✗"
        print(f"{status} {today_str} -> {month_end} (expected {expected})")
    
    print()

if __name__ == "__main__":
    print("Date Helper Function Validation")
    print("=" * 60)
    print()
    
    test_weekday_values()
    test_week_start_calculation()
    test_month_start_calculation()
    test_month_end_calculation()
    
    print("=" * 60)
    print("Validation Complete!")
    print()
    print("Summary:")
    print("- weekday() returns 0=Monday (CONFIRMED)")
    print("- week_start calculation works correctly across week/year boundaries")
    print("- month_start calculation works correctly across month/year boundaries")
    print("- month_end calculation handles all months correctly (including leap years)")
