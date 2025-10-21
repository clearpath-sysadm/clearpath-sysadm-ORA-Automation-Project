#!/usr/bin/env python3
"""
Production Workflow Health Check
Verifies that all automation workflows are running in production environment
"""
import os
import sys
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.database.db_adapter import get_connection

def check_environment():
    """Check if running in production deployment"""
    is_production = os.getenv('REPLIT_DEPLOYMENT') == '1'
    repl_slug = os.getenv('REPL_SLUG', 'unknown')
    
    print("=" * 80)
    print("🔍 ENVIRONMENT CHECK")
    print("=" * 80)
    print(f"Environment: {'PRODUCTION' if is_production else 'DEVELOPMENT'}")
    print(f"Repl Slug: {repl_slug}")
    print(f"REPLIT_DEPLOYMENT: {os.getenv('REPLIT_DEPLOYMENT', 'not set')}")
    print()
    
    return is_production

def check_workflow_status():
    """Check when workflows last ran based on database timestamps"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT name, last_run_at, enabled
            FROM workflows
            ORDER BY name
        """)
        
        workflows = cursor.fetchall()
        
        print("=" * 80)
        print("📊 WORKFLOW STATUS (from database)")
        print("=" * 80)
        
        now = datetime.now(timezone.utc)
        all_healthy = True
        
        for workflow_name, last_run_at, enabled in workflows:
            if not enabled:
                status = "⏸️  DISABLED"
            elif last_run_at is None:
                status = "❌ NEVER RAN"
                all_healthy = False
            else:
                # Parse timestamp if it's a string
                if isinstance(last_run_at, str):
                    last_run_at = datetime.fromisoformat(last_run_at.replace('Z', '+00:00'))
                # Convert to timezone-aware if needed
                elif last_run_at.tzinfo is None:
                    last_run_at = last_run_at.replace(tzinfo=timezone.utc)
                
                age_seconds = (now - last_run_at).total_seconds()
                age_minutes = age_seconds / 60
                
                # Different workflows have different expected intervals
                expected_intervals = {
                    'unified-shipstation-sync': 5,  # 5 minutes
                    'shipstation-upload': 5,        # 5 minutes
                    'xml-import': 5,                # 5 minutes (fast polling)
                    'duplicate-scanner': 15,        # 15 minutes
                    'lot-mismatch-scanner': 15,     # 15 minutes
                    'orders-cleanup': 1440,         # 24 hours
                    'weekly-reporter': 10080,       # 7 days (on-demand)
                }
                
                max_age = expected_intervals.get(workflow_name, 10) * 2  # 2x expected interval
                
                if age_minutes < max_age:
                    status = f"✅ {int(age_minutes)} min ago"
                else:
                    status = f"⚠️  {int(age_minutes)} min ago (STALE)"
                    all_healthy = False
            
            print(f"{workflow_name:30s} {status}")
        
        print()
        print("=" * 80)
        if all_healthy:
            print("✅ All enabled workflows are healthy!")
        else:
            print("⚠️  Some workflows may not be running!")
        print("=" * 80)
        
        return all_healthy
        
    finally:
        cursor.close()
        conn.close()

def check_processes():
    """Check if workflow processes are actually running (Linux only)"""
    print()
    print("=" * 80)
    print("🔧 RUNNING PROCESSES")
    print("=" * 80)
    
    # Check for Python processes running our workflows
    os.system("ps aux | grep -E 'scheduled_|unified_shipstation_sync' | grep -v grep || echo 'No workflow processes found'")
    print()

if __name__ == "__main__":
    print()
    is_prod = check_environment()
    is_healthy = check_workflow_status()
    
    if is_prod:
        check_processes()
    else:
        print("💡 TIP: This is development. Production uses REPLIT_DEPLOYMENT=1")
    
    print()
    
    # Exit code: 0 = healthy, 1 = unhealthy
    sys.exit(0 if is_healthy else 1)
