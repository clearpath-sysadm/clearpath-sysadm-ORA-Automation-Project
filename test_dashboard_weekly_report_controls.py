from pathlib import Path


def test_weekly_report_does_not_render_adjust_buttons():
    html = Path(__file__).with_name("index.html").read_text(encoding="utf-8")
    report_start = html.index("async function loadWeeklyReport()")
    report_end = html.index("// Copy weekly inventory to clipboard", report_start)
    report_loader = html[report_start:report_end]

    assert "openPhysicalCountModal(" not in report_loader
    assert "Adjust inventory from physical count" not in report_loader


def test_weekly_report_uses_cards_at_mobile_and_tablet_widths():
    html = Path(__file__).with_name("index.html").read_text(encoding="utf-8")

    assert "window.matchMedia('(max-width: 768px)').matches" in html
    assert "#weeklyReportTable { display: none !important; }" in html
    assert "#weeklyReportCards.weekly-report-ready { display: flex !important; }" in html
    assert ".weekly-inv-card-stats .wic-sep { display: none; }" in html
    assert "window.addEventListener('resize', updateWeeklyReportLayout)" in html