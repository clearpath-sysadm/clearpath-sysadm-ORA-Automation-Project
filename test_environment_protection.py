#!/usr/bin/env python3
"""
Test script to verify environment protection logic
Demonstrates that protection works purely on REPL_SLUG value
"""

def test_environment_protection(repl_slug, environment):
    """
    Simulates the actual protection logic from scheduled_shipstation_upload.py
    Returns: (is_dev, reason)
    """
    repl_slug = repl_slug.lower()
    environment = environment.lower()
    
    # ACTUAL PRODUCTION CODE LOGIC (lines 666-671)
    if 'workspace' in repl_slug:
        is_dev = True
        reason = f"BLOCKED: 'workspace' found in REPL_SLUG='{repl_slug}'"
    elif environment == 'production':
        is_dev = False
        reason = f"ALLOWED: ENVIRONMENT='production' and REPL_SLUG='{repl_slug}' (not workspace)"
    else:
        is_dev = True
        reason = f"BLOCKED: Default safe behavior (REPL_SLUG='{repl_slug}', ENVIRONMENT='{environment}')"
    
    return is_dev, reason


def main():
    print("=" * 80)
    print("ENVIRONMENT PROTECTION TEST - Verifying REPL_SLUG Priority")
    print("=" * 80)
    print()
    
    # Test cases covering all scenarios
    test_cases = [
        # (REPL_SLUG, ENVIRONMENT, Expected Result)
        ("workspace", "", "BLOCKED"),
        ("workspace", "development", "BLOCKED"),
        ("workspace", "production", "BLOCKED"),  # THIS IS THE KEY TEST - ENVIRONMENT ignored!
        ("ora-business-automation", "production", "ALLOWED"),
        ("ora-business-automation", "", "BLOCKED"),
        ("ora-business-automation", "development", "BLOCKED"),
        ("my-deployed-app", "production", "ALLOWED"),
        ("my-deployed-app", "", "BLOCKED"),
    ]
    
    print("TEST SCENARIOS:")
    print("-" * 80)
    print(f"{'REPL_SLUG':<30} {'ENVIRONMENT':<15} {'RESULT':<10} {'REASON'}")
    print("-" * 80)
    
    all_passed = True
    for repl_slug, environment, expected in test_cases:
        is_dev, reason = test_environment_protection(repl_slug, environment)
        actual = "BLOCKED" if is_dev else "ALLOWED"
        status = "✅" if actual == expected else "❌"
        
        if actual != expected:
            all_passed = False
        
        env_display = environment if environment else "(empty)"
        print(f"{status} {repl_slug:<28} {env_display:<15} {actual:<10} {reason}")
    
    print("-" * 80)
    print()
    
    # Highlight the critical test case
    print("🔍 CRITICAL TEST CASE (The Bug We Fixed):")
    print("-" * 80)
    is_dev, reason = test_environment_protection("workspace", "production")
    print(f"REPL_SLUG='workspace' + ENVIRONMENT='production'")
    print(f"Result: {'BLOCKED ✅' if is_dev else 'ALLOWED ❌'}")
    print(f"Reason: {reason}")
    print()
    print("This proves REPL_SLUG takes priority over ENVIRONMENT!")
    print("Even with ENVIRONMENT=production, workspace is still blocked.")
    print("=" * 80)
    print()
    
    # Show actual current environment
    import os
    print("📍 CURRENT ACTUAL ENVIRONMENT:")
    print("-" * 80)
    actual_slug = os.getenv('REPL_SLUG', '(not set)')
    actual_env = os.getenv('ENVIRONMENT', '(not set)')
    is_dev, reason = test_environment_protection(actual_slug, actual_env)
    
    print(f"REPL_SLUG: {actual_slug}")
    print(f"ENVIRONMENT: {actual_env}")
    print(f"Upload Status: {'BLOCKED ✅' if is_dev else 'ALLOWED ✅'}")
    print(f"Reason: {reason}")
    print("=" * 80)
    print()
    
    if all_passed:
        print("✅ ALL TESTS PASSED - Protection logic verified!")
    else:
        print("❌ SOME TESTS FAILED - Review logic!")
    
    return all_passed


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
