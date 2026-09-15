from pathlib import Path


def test_dashboard_links_to_dedicated_operations_reports():
    html = Path(__file__).with_name("index.html").read_text(encoding="utf-8")

    for href, label in (
        ("/shipment_summary.html", "Today's Pick List"),
        ("/weekly_inventory_report.html", "Weekly Inventory Report"),
        ("/charge_report.html", "Monthly Charge Report"),
    ):
        assert f'href="{href}"' in html
        assert label in html


def test_dashboard_does_not_embed_weekly_inventory_report():
    html = Path(__file__).with_name("index.html").read_text(encoding="utf-8")

    assert 'id="weeklyReportTable"' not in html
    assert 'id="weeklyReportCards"' not in html
    assert 'id="weeklyReportLoading"' not in html
    assert 'id="inventory-risk-section"' not in html
    assert "loadWeeklyReport();" not in html


def test_time_log_is_last_dashboard_section():
    html = Path(__file__).with_name("index.html").read_text(encoding="utf-8")
    assert html.index('id="report-navigation-section"') < html.index('id="time-log-section"')
    assert 'id="time-log-section" style="margin-bottom: 0;"' in html
    assert 'id="time-log-toggle" type="button"' in html
    assert 'aria-expanded="false" aria-controls="tl-body"' in html
    assert "toggle.setAttribute('aria-expanded', String(!isOpen));" in html


def test_removed_weekly_report_resize_handler_is_gone():
    html = Path(__file__).with_name("index.html").read_text(encoding="utf-8")
    assert "window.addEventListener('resize', updateWeeklyReportLayout);" not in html