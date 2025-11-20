#!/usr/bin/env python3
"""
Oracare Fulfillment System - Secrets Migration Helper

This script helps you transfer secrets between Repls by:
1. Listing required secrets in the original Repl
2. Validating secrets exist in the new Repl
3. Providing a checklist for manual transfer

SECURITY NOTE: This script NEVER exports actual secret values.
You must manually copy values through the Replit Secrets UI.

Usage:
    # In ORIGINAL Repl - Generate checklist
    python secrets_checklist.py check
    
    # In NEW Repl - Verify all secrets are configured
    python secrets_checklist.py verify
"""

import os
import sys
from datetime import datetime

# Required secrets for Oracare Fulfillment System
REQUIRED_SECRETS = {
    'SHIPSTATION_API_KEY': {
        'description': 'ShipStation API Key for order uploads',
        'category': 'ShipStation',
        'critical': True
    },
    'SHIPSTATION_API_SECRET': {
        'description': 'ShipStation API Secret for authentication',
        'category': 'ShipStation',
        'critical': True
    },
    'BENCO_FEDEX_ACCOUNT_ID': {
        'description': 'FedEx Account ID for Benco shipments',
        'category': 'Shipping',
        'critical': True
    },
    'ADMIN_EMAILS': {
        'description': 'Comma-separated list of admin email addresses',
        'category': 'Access Control',
        'critical': True
    },
    'SESSION_SECRET': {
        'description': 'Flask session secret for authentication',
        'category': 'Security',
        'critical': True
    }
}

# Auto-generated secrets (created by Replit, don't transfer)
AUTO_GENERATED = {
    'DATABASE_URL': 'PostgreSQL connection string (auto-generated)',
    'PGHOST': 'PostgreSQL host (auto-generated)',
    'PGPORT': 'PostgreSQL port (auto-generated)',
    'PGUSER': 'PostgreSQL user (auto-generated)',
    'PGPASSWORD': 'PostgreSQL password (auto-generated)',
    'PGDATABASE': 'PostgreSQL database name (auto-generated)',
}

def check_secrets():
    """Check which secrets exist in current environment and generate checklist."""
    print("=" * 70)
    print("  Secrets Migration Checklist - ORIGINAL Repl")
    print("=" * 70)
    print()
    
    print("🔒 Checking required secrets in current environment...")
    print()
    
    found_secrets = []
    missing_secrets = []
    
    for secret_name, info in REQUIRED_SECRETS.items():
        exists = os.getenv(secret_name) is not None
        
        if exists:
            # Show first 4 chars and last 4 chars if long enough
            value = os.getenv(secret_name)
            if len(value) > 12:
                masked = f"{value[:4]}...{value[-4:]}"
            else:
                masked = "***" * len(value)
            
            status = "✅ SET"
            found_secrets.append((secret_name, info, masked))
        else:
            status = "❌ MISSING"
            missing_secrets.append((secret_name, info))
        
        critical = "🔴 CRITICAL" if info['critical'] else "⚪ Optional"
        print(f"{status} {critical} {secret_name}")
        print(f"       {info['description']}")
        print()
    
    if missing_secrets:
        print("⚠️  WARNING: Some required secrets are missing!")
        print("   Set these in the Secrets tool before migration.")
        print()
    
    # Generate transfer checklist
    print("=" * 70)
    print("  📋 MANUAL TRANSFER CHECKLIST")
    print("=" * 70)
    print()
    print("Copy the following secrets from THIS Repl to your NEW Repl:")
    print()
    print("In ORIGINAL Repl (this one):")
    print("1. Click Tools → Secrets (or 🔒 icon)")
    print("2. For each secret below, click the eye icon to view the value")
    print("3. Copy the value to your clipboard")
    print()
    print("In NEW Repl:")
    print("1. Click Tools → Secrets")
    print("2. Click + New Secret")
    print("3. Enter the name and paste the value")
    print("4. Click Add Secret")
    print()
    print("-" * 70)
    
    for i, (secret_name, info, masked) in enumerate(found_secrets, 1):
        print(f"\n{i}. {secret_name}")
        print(f"   Category: {info['category']}")
        print(f"   Description: {info['description']}")
        print(f"   Current value (masked): {masked}")
        print(f"   [ ] Copied to new Repl")
    
    print()
    print("-" * 70)
    print()
    print("🚫 DO NOT TRANSFER (auto-generated in new Repl):")
    for secret_name, description in AUTO_GENERATED.items():
        print(f"   ⚪ {secret_name} - {description}")
    
    print()
    print("=" * 70)
    print(f"Total secrets to transfer: {len(found_secrets)}")
    print("=" * 70)
    print()
    
    # Save checklist to file
    checklist_file = f"secrets_checklist_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(checklist_file, 'w') as f:
        f.write("Oracare Fulfillment System - Secrets Transfer Checklist\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 70 + "\n\n")
        
        for i, (secret_name, info, masked) in enumerate(found_secrets, 1):
            f.write(f"{i}. {secret_name}\n")
            f.write(f"   Category: {info['category']}\n")
            f.write(f"   Description: {info['description']}\n")
            f.write(f"   Value (masked): {masked}\n")
            f.write(f"   [ ] Transferred to new Repl\n\n")
    
    print(f"📄 Checklist saved to: {checklist_file}")
    print()

def verify_secrets():
    """Verify all required secrets exist in new environment."""
    print("=" * 70)
    print("  Secrets Verification - NEW Repl")
    print("=" * 70)
    print()
    
    print("🔍 Verifying required secrets in new environment...")
    print()
    
    all_present = True
    missing_critical = []
    
    for secret_name, info in REQUIRED_SECRETS.items():
        exists = os.getenv(secret_name) is not None
        
        if exists:
            value = os.getenv(secret_name)
            has_value = value and len(value.strip()) > 0
            
            if has_value:
                status = "✅ CONFIGURED"
                # Show length for verification
                print(f"{status} {secret_name} (length: {len(value)} chars)")
            else:
                status = "⚠️  EMPTY"
                print(f"{status} {secret_name} - exists but empty!")
                all_present = False
                if info['critical']:
                    missing_critical.append(secret_name)
        else:
            status = "❌ MISSING"
            print(f"{status} {secret_name}")
            all_present = False
            if info['critical']:
                missing_critical.append(secret_name)
        
        print(f"       {info['description']}")
        print()
    
    # Check auto-generated database secrets
    print("🔍 Checking auto-generated database secrets...")
    print()
    
    db_secrets_ok = True
    for secret_name, description in AUTO_GENERATED.items():
        exists = os.getenv(secret_name) is not None
        
        if exists:
            print(f"✅ {secret_name}")
        else:
            print(f"❌ {secret_name} - MISSING!")
            db_secrets_ok = False
    
    print()
    print("=" * 70)
    
    if all_present and db_secrets_ok:
        print("✅ SUCCESS! All secrets configured correctly")
        print("=" * 70)
        print()
        print("Your new Repl is ready to run!")
        print("Next step: python migrate_data.py import")
        print()
        return 0
    else:
        print("❌ VERIFICATION FAILED")
        print("=" * 70)
        print()
        
        if missing_critical:
            print("🔴 Critical secrets missing:")
            for secret in missing_critical:
                print(f"   - {secret}")
            print()
        
        if not db_secrets_ok:
            print("⚠️  Database secrets missing!")
            print("   Action: Create PostgreSQL database in Replit")
            print("   Tools → PostgreSQL → Create Database")
            print()
        
        print("Please configure missing secrets before proceeding.")
        print()
        return 1

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Oracare Fulfillment System - Secrets Migration Helper")
        print()
        print("Usage:")
        print("  python secrets_checklist.py check    # Generate transfer checklist (original Repl)")
        print("  python secrets_checklist.py verify   # Verify secrets configured (new Repl)")
        print()
        return 1
    
    command = sys.argv[1].lower()
    
    if command == 'check':
        check_secrets()
        return 0
    elif command == 'verify':
        return verify_secrets()
    else:
        print(f"Unknown command: {command}")
        print("Use 'check' or 'verify'")
        return 1

if __name__ == '__main__':
    sys.exit(main())
