"""Focused coverage for the canonical static application sidebar."""

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SHARED_PAGES = {
    "index.html": None,
    "charge_report.html": "/charge_report.html",
    "email_contacts.html": "/email_contacts.html",
    "help.html": "/help.html",
    "incidents.html": None,
    "inventory.html": None,
    "inventory_snapshots.html": "/inventory_snapshots.html",
    "inventory_transactions.html": "/inventory_transactions.html",
    "logs.html": "/logs.html",
    "lot_inventory.html": "/lot_inventory.html",
    "order-management.html": "/order-management.html",
    "settings.html": "/settings.html",
    "shipment_summary.html": "/shipment_summary.html",
    "shipped_items.html": "/shipped_items.html",
    "shipped_orders.html": "/shipped_orders.html",
    "weekly_shipped_history.html": "/weekly_shipped_history.html",
    "workflow_controls.html": "/workflow_controls.html",
}
CANONICAL_LINKS = [
    ("/shipment_summary.html", "Today's Pick List"),
    ("/xml_import.html", "New Orders"),
    ("/inventory_transactions.html", "Inventory Monitor"),
    ("/lot_inventory.html", "Lot Inventory"),
    ("/shipped_orders.html", "Shipped Orders"),
    ("/shipped_items.html", "Shipped Items"),
    ("/order-management.html", "Order Corrections"),
    ("/charge_report.html", "Charge Report"),
    ("/weekly_shipped_history.html", "Weekly Reports"),
    ("/sku_lot.html", "SKU Lot Management"),
    ("/inventory_snapshots.html", "Inventory Snapshots"),
    ("/email_contacts.html", "Email Contacts"),
    ("/workflow_controls.html", "Workflow Controls"),
    ("/logs.html", "Server Logs"),
    ("/help.html", "Help & Training"),
    ("/settings.html", "Settings"),
]


def nav_for(filename):
    source = (ROOT / filename).read_text()
    match = re.search(r'<nav class="sidebar-nav">([\s\S]*?)</nav>', source)
    assert match, f"{filename} should use the shared static sidebar"
    return match.group(0)


def links_in(nav):
    links = re.findall(
        r'<a href="([^"]+)" class="nav-item(?: active)?"[^>]*>([\s\S]*?)</a>',
        nav,
    )
    return [
        (href, re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", body)).strip())
        for href, body in links
    ]


def test_canonical_sidebar_is_identical_on_all_shared_pages():
    for filename in SHARED_PAGES:
        nav = nav_for(filename)
        assert links_in(nav) == CANONICAL_LINKS, filename
        for heading in ("Fulfillment", "Orders History", "Reports"):
            assert heading in nav
        assert "Catalog & Config" in nav or "Catalog &amp; Config" in nav
        assert 'class="admin-items"' in nav
        assert "order_audit.html" not in nav
        assert "bundle_skus.html" not in nav
        assert "Report Issue" not in nav


def test_each_canonical_link_has_a_distinct_inline_svg_icon():
    nav = nav_for("index.html")
    anchors = re.findall(
        r'<a href="([^"]+)" class="nav-item(?: active)?"[^>]*>([\s\S]*?)</a>',
        nav,
    )
    assert len(anchors) == len(CANONICAL_LINKS)
    icons = []
    for href, body in anchors:
        assert '<span class="nav-item-icon"><svg ' in body, href
        assert not re.search(r"[\U0001F000-\U0010FFFF]", body), href
        icons.append(re.search(r'<svg [\s\S]*?</svg>', body).group(0))
    assert len(set(icons)) == len(CANONICAL_LINKS)


def test_sidebar_active_item_matches_each_page():
    for filename, active_href in SHARED_PAGES.items():
        active = re.findall(
            r'<a href="([^"]+)" class="nav-item active">', nav_for(filename)
        )
        assert active == ([active_href] if active_href else []), filename


def test_retired_pages_are_not_in_route_whitelist():
    source = (ROOT / "app.py").read_text()
    match = re.search(r"^ALLOWED_PAGES\s*=\s*(\[.*\])$", source, re.MULTILINE)
    assert match
    allowed = ast.literal_eval(match.group(1))
    assert "order_audit.html" not in allowed
    assert "bundle_skus.html" not in allowed


def test_page_specific_sidebar_controls_are_preserved():
    dashboard = (ROOT / "index.html").read_text()
    logs = (ROOT / "logs.html").read_text()

    assert 'id="charge-report-link"' in dashboard
    assert 'id="user-widget"' in dashboard
    assert 'id="user-widget"' in logs