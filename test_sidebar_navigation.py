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
    "settings.html": "/settings.html",
    "shipment_summary.html": "/shipment_summary.html",
    "shipped_items.html": "/shipped_items.html",
    "shipped_orders.html": "/shipped_orders.html",
    "weekly_inventory_report.html": "/weekly_inventory_report.html",
    "weekly_shipped_history.html": "/weekly_shipped_history.html",
    "workflow_controls.html": "/workflow_controls.html",
}
CANONICAL_LINKS = [
    ("/shipment_summary.html", "Today's Pick List"),
    ("/inventory_transactions.html", "Inventory Monitor"),
    ("/lot_inventory.html", "Lot Inventory"),
    ("/weekly_inventory_report.html", "Weekly Inventory Report"),
    ("/charge_report.html", "Monthly Charge Report"),
    ("/weekly_shipped_history.html", "Shipping History"),
    ("/shipped_orders.html", "Shipped Orders"),
    ("/shipped_items.html", "Shipped Items"),
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
    retired_hrefs = {"/xml_import.html", "/order-management.html"}
    return [
        (href, re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", body)).strip())
        for href, body in links
        if href not in retired_hrefs
    ]


def test_canonical_sidebar_is_identical_on_all_shared_pages():
    for filename in SHARED_PAGES:
        nav = nav_for(filename)
        assert links_in(nav) == CANONICAL_LINKS, filename
        for heading in ("Fulfillment", "Orders History", "Reports"):
            assert heading in nav
        assert "Catalog & Config" in nav or "Catalog &amp; Config" in nav
        assert 'class="admin-items"' in nav
        assert 'id="orders-history-section"' in nav
        assert "/weekly_shipped_history.html" in nav
        assert "order_audit.html" not in nav
        assert "bundle_skus.html" not in nav
        assert "Report Issue" not in nav

def test_sidebar_sections_have_canonical_static_structure():
    for filename in SHARED_PAGES:
        nav = nav_for(filename)
        fulfillment = re.search(
            r'<div class="nav-section">\s*'
            r'<div class="nav-section-title">Fulfillment</div>',
            nav,
        )
        reports = re.search(
            r'<div class="nav-section">\s*'
            r'<div class="nav-section-title">Reports</div>'
            r'([\s\S]*?)</div>',
            nav,
        )
        orders = re.search(
            r'<div class="nav-section admin-section orders-history-section" '
            r'id="orders-history-section">([\s\S]*?)</div>\s*</div>',
            nav,
        )
        assert fulfillment and reports and orders, filename
        assert (
            nav.index(fulfillment.group(0))
            < nav.index(reports.group(0))
            < nav.index(orders.group(0))
        ), filename
        assert '<div class="admin-toggle"' not in reports.group(0), filename
        assert 'class="admin-items"' not in reports.group(0), filename
        assert "data-monthly-charge-label" not in reports.group(0), filename
        assert re.findall(
            r'<a href="([^"]+)" class="nav-item(?: active)?"',
            reports.group(0),
        ) == ["/weekly_inventory_report.html", "/charge_report.html"], filename
        assert re.findall(
            r'<a href="([^"]+)" class="nav-item(?: active)?"',
            orders.group(0),
        ) == [
            "/weekly_shipped_history.html",
            "/shipped_orders.html",
            "/shipped_items.html",
            "/order-management.html",
            "/inventory_snapshots.html",
        ], filename
def test_each_canonical_link_has_a_distinct_inline_svg_icon():
    nav = nav_for("index.html")
    anchors = re.findall(
        r'<a href="([^"]+)" class="nav-item(?: active)?"[^>]*>([\s\S]*?)</a>',
        nav,
    )
    anchors = [
        anchor for anchor in anchors
        if anchor[0] not in {"/xml_import.html", "/order-management.html"}
    ]
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

def test_orders_history_active_items_and_all_history_links_are_preserved():
    history_pages = {
        "weekly_shipped_history.html": "/weekly_shipped_history.html",
        "shipped_orders.html": "/shipped_orders.html",
        "shipped_items.html": "/shipped_items.html",
        "inventory_snapshots.html": "/inventory_snapshots.html",
    }
    for filename, active_href in history_pages.items():
        nav = nav_for(filename)
        assert active_href in dict(links_in(nav)), filename
        assert f'href="{active_href}" class="nav-item active"' in nav, filename
        for href in (
            "/weekly_shipped_history.html",
            "/shipped_orders.html",
            "/shipped_items.html",
            "/inventory_snapshots.html",
        ):
            assert href in nav, filename
def test_shipped_troubleshooting_links_are_admin_opt_in():
    css = (ROOT / "static/css/global-styles.css").read_text()
    auth = (ROOT / "static/js/auth.js").read_text()
    settings = (ROOT / "settings.html").read_text()
    app = (ROOT / "app.py").read_text()

    for href in (
        "/weekly_shipped_history.html",
        "/shipped_orders.html",
        "/shipped_items.html",
        "/inventory_snapshots.html",
    ):
        assert href in nav_for("index.html")
        assert f"'{href.lstrip('/')}'" in app

    assert "body.show-orders-history" in css
    assert "showOrdersHistory" in auth
    assert "this.isAdmin()" in auth
    assert "applyNavigationPreferences()" in auth
    assert 'id="troubleshootingNavigationSettings"' in settings
    assert "data-admin-only hidden" in settings
    assert 'id="showOrdersHistory"' in settings
    assert "localStorage.removeItem('showOrdersHistory')" in settings
    for label in (
        "Orders History",
        "Shipping History",
        "Shipped Orders",
        "Shipped Items",
        "Inventory Snapshots",
    ):
        assert label in settings


def test_retired_pages_are_not_in_route_whitelist():
    source = (ROOT / "app.py").read_text()
    match = re.search(r"^ALLOWED_PAGES\s*=\s*(\[.*\])$", source, re.MULTILINE)
    assert match
    allowed = ast.literal_eval(match.group(1))
    assert "order_audit.html" not in allowed
    assert "bundle_skus.html" not in allowed
    assert "xml_import.html" not in allowed
    assert "order-management.html" not in allowed
    assert "sku_lot.html" not in allowed


def test_retired_order_pages_are_hidden_from_navigation():
    styles = (ROOT / "static/css/global-styles.css").read_text()
    assert '.sidebar-nav a[href="/xml_import.html"]' in styles
    assert '.sidebar-nav a[href="/order-management.html"]' in styles


def test_outdated_help_page_is_hidden_from_navigation_but_remains_available():
    styles = (ROOT / "static/css/global-styles.css").read_text()
    app = (ROOT / "app.py").read_text()
    match = re.search(r"^ALLOWED_PAGES\s*=\s*(\[.*\])$", app, re.MULTILINE)

    assert '.sidebar-nav a[href="/help.html"]' in styles
    assert match
    assert "help.html" in ast.literal_eval(match.group(1))
    assert (ROOT / "help.html").exists()


def test_retired_sku_lot_page_does_not_remove_live_assignments():
    app = (ROOT / "app.py").read_text()
    lot_inventory = (ROOT / "lot_inventory.html").read_text()
    retired_page = ROOT / "sku_lot.html"

    assert retired_page.exists()
    for nav_file in SHARED_PAGES:
        assert "/sku_lot.html" not in nav_for(nav_file), nav_file
    for route in (
        "@app.route('/api/sku_lots', methods=['GET'])",
        "@app.route('/api/sku_lots', methods=['POST'])",
        "@app.route('/api/sku_lots/<int:sku_lot_id>', methods=['PUT'])",
        "@app.route('/api/sku_lots/<int:sku_lot_id>', methods=['DELETE'])",
    ):
        assert route in app
    assert 'id="pane-assignments"' in lot_inventory
    assert "loadSkuLots()" in lot_inventory
    assert "saveInlineAssignment()" in lot_inventory
    assert "saveSkuLot()" in lot_inventory
    assert "toggleSkuLotActive" in lot_inventory


def test_weekly_inventory_report_uses_one_accessible_action_dropdown():
    page = (ROOT / "weekly_inventory_report.html").read_text()

    assert 'id="reportActionsTrigger"' in page
    assert 'aria-haspopup="menu"' in page
    assert 'aria-controls="reportActionsMenu"' in page
    assert 'id="reportActionsMenu" role="menu" hidden' in page
    for action in ("compose", "refresh", "eod", "eow", "eom"):
        assert f'id="action-{action}"' in page
    assert 'href="/email_contacts.html" role="menuitem"' in page
    for retired_control in (
        'id="copyInventoryBtn"',
        'id="weeklyReportRefreshBtn"',
        'id="btn-eod"',
        'id="btn-eow"',
        'id="btn-eom"',
    ):
        assert retired_control not in page
    assert "beginReportAction(action" in page
    assert "if (reportActionInProgress) return false" in page
    assert "closeReportActionsMenu({restoreFocus: true})" in page
    assert "['ArrowDown', 'ArrowUp', 'Home', 'End']" in page


def test_weekly_inventory_report_action_menu_stays_anchored_on_mobile():
    page = (ROOT / "weekly_inventory_report.html").read_text()
    base_menu_rule = re.search(
        r"\.report-actions-menu\s*\{([^}]*)\}",
        page,
    )
    mobile_rules = re.search(
        r"@media \(max-width: 768px\)\s*\{([\s\S]*?)\n\s*\}\n\s*</style>",
        page,
    )

    assert base_menu_rule
    assert "position: absolute" in base_menu_rule.group(1)
    assert "top: calc(100% + 6px)" in base_menu_rule.group(1)
    assert "right: 0" in base_menu_rule.group(1)
    assert "width: min(310px, calc(100vw - 48px))" in base_menu_rule.group(1)
    assert mobile_rules
    assert "position: fixed" not in mobile_rules.group(1)
    assert "bottom:" not in mobile_rules.group(1)


def test_weekly_inventory_report_keeps_current_inventory_workflow():
    source = (ROOT / "weekly_inventory_report.html").read_text()
    app = (ROOT / "app.py").read_text()

    assert "weekly_inventory_report.html" in app
    assert "/api/weekly_inventory_report" in source
    assert "/api/reports/status" in source
    for report_type in ("EOD", "EOW", "EOM"):
        assert f"runReport('{report_type}')" in source
    for heading in ("Current Qty", "Pallet Breakdown", "52-Week Avg", "Days Left"):
        assert heading in source
    assert 'id="weeklyReportCards"' in source
    assert "weekly-inv-card" in source
    assert 'href="/email_contacts.html"' in source


def test_page_specific_sidebar_controls_are_preserved():
    dashboard = (ROOT / "index.html").read_text()
    logs = (ROOT / "logs.html").read_text()

    assert 'id="charge-report-link"' in dashboard
    assert 'id="user-widget"' in dashboard
    assert 'id="user-widget"' in logs
