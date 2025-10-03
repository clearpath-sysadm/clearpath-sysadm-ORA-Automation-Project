#!/usr/bin/env python3
"""
Script to add shipping violations alert to all HTML pages
"""

import os
import re

# Pages to update (excluding index.html which already has it)
HTML_FILES = [
    'shipped_items.html',
    'bundle_skus.html',
    'sku_lot.html',
    'xml_import.html',
    'shipped_orders.html',
    'charge_report.html',
    'weekly_shipped_history.html',
    'inventory_transactions.html',
    'settings.html'
]

# Read the alert HTML
with open('static/shipping-violations-alert.html', 'r') as f:
    alert_html = f.read()

# CSS link to add
css_link = '    <link rel="stylesheet" href="/static/shipping-violations-alert.css">\n'

# JS script to add
js_script = '    <script src="/static/shipping-violations-alert.js"></script>\n'

for html_file in HTML_FILES:
    file_path = html_file
    
    if not os.path.exists(file_path):
        print(f"⏭️  Skipping {html_file} (not found)")
        continue
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if already has the alert
    if 'violations-alert' in content:
        print(f"✅ {html_file} already has violations alert")
        continue
    
    # 1. Add CSS link in <head> before </head>
    if '/static/shipping-violations-alert.css' not in content:
        content = content.replace('</head>', f'{css_link}</head>')
    
    # 2. Add alert HTML after <body>
    content = content.replace('<body>', f'<body>\n{alert_html}\n')
    
    # 3. Add JS script before </body>
    if '/static/shipping-violations-alert.js' not in content:
        content = content.replace('</body>', f'{js_script}</body>')
    
    # Write back
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Added violations alert to {html_file}")

print("\n🎉 Done! Violations alert added to all pages.")
