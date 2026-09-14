from pathlib import Path


INDEX_HTML = Path(__file__).with_name("index.html")


def _dashboard_html():
    return INDEX_HTML.read_text(encoding="utf-8")


def test_compact_pulse_keeps_all_live_data_targets():
    html = _dashboard_html()
    required_ids = (
        "units-to-pick-value",
        "on-hold-units",
        "benco-orders-value",
        "hawaiian-orders-value",
        "canadian-orders-value",
        "intl-orders-value",
        "pulse-orders-today-value",
        "pulse-last-order-value",
        "pulse-last-sync-value",
    )

    for element_id in required_ids:
        assert f'id="{element_id}"' in html


def test_compact_pulse_omits_system_condition_cards():
    html = _dashboard_html()

    assert 'id="system-status-card"' not in html
    assert 'id="production-health-card"' not in html
    assert 'class="pulse-workload-grid"' in html
    assert 'class="pulse-activity-panel"' in html


def test_dashboard_refreshes_recent_activity_data():
    html = _dashboard_html()
    refresh_start = html.index("async function refreshDashboard()")
    refresh_end = html.index("// Show Discrepancy Details Modal", refresh_start)
    refresh_function = html[refresh_start:refresh_end]

    assert "loadSystemPulse()" in refresh_function