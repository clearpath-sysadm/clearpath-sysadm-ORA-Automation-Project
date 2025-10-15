#!/usr/bin/env python3
"""Extract SQLite schema for PostgreSQL conversion"""

import sqlite3

# Connect to SQLite
conn = sqlite3.connect('ora.db')
cursor = conn.cursor()

# Get all CREATE TABLE statements
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL;")
tables = cursor.fetchall()

print("-- SQLite Schema Extracted from ora.db")
print("-- Total tables:", len(tables))
print()

for table_sql in tables:
    print(table_sql[0] + ";")
    print()

# Get all CREATE INDEX statements
cursor.execute("SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL;")
indexes = cursor.fetchall()

if indexes:
    print("-- Indexes")
    for index_sql in indexes:
        print(index_sql[0] + ";")
        print()

conn.close()
