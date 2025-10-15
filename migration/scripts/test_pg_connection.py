#!/usr/bin/env python3
"""Test PostgreSQL connection"""

import os
import sys

try:
    import psycopg2
    
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL environment variable not set")
        print("   PostgreSQL database may not be created yet")
        sys.exit(1)
    
    print("🔍 Testing PostgreSQL connection...")
    print(f"   Connection string: {DATABASE_URL[:30]}...")
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Get PostgreSQL version
    cur.execute('SELECT version();')
    version = cur.fetchone()[0]
    
    # Test write capability
    cur.execute("CREATE TABLE IF NOT EXISTS _test_connection (id SERIAL PRIMARY KEY, test TEXT);")
    cur.execute("INSERT INTO _test_connection (test) VALUES ('migration_test');")
    cur.execute("SELECT test FROM _test_connection WHERE test = 'migration_test';")
    result = cur.fetchone()
    cur.execute("DROP TABLE _test_connection;")
    
    conn.commit()
    conn.close()
    
    print(f"✅ PostgreSQL connected successfully")
    print(f"   Version: {version[:60]}...")
    print(f"   Read/Write: OK")
    print(f"   Connection: VERIFIED")
    
except ImportError:
    print("❌ psycopg2 not installed")
    print("   Run: pip install psycopg2-binary")
    sys.exit(1)
except Exception as e:
    print(f"❌ Connection failed: {e}")
    sys.exit(1)
