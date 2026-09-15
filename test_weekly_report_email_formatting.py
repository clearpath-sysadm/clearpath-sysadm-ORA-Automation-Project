from pathlib import Path


def test_compose_email_copies_rich_table_with_plain_text_fallback():
    source = Path(__file__).with_name("weekly_inventory_report.html").read_text(
        encoding="utf-8"
    )
    compose = source[source.index("async function composeWeeklyInventoryEmail()") :]

    assert "const htmlRows = report.data.map" in compose
    assert "'text/html': new Blob([html], {type: 'text/html'})" in compose
    assert "'text/plain': new Blob([text], {type: 'text/plain'})" in compose
    assert "new ClipboardItem" in compose
    assert "await navigator.clipboard.writeText(text);" in compose
    for heading in (
        "Product",
        "Current Qty",
        "52-Week Avg",
        "Days Left",
    ):
        assert f">{heading}</th>" in compose
    assert 'background-color:#f3f4f6;' in compose
    assert ">Pallet Breakdown</th>" not in compose
    assert "const palletBreakdown =" not in compose
    assert "Product | Current Qty | 52-Week Avg | Days Left" in compose


def test_weekly_report_auto_refreshes_safely_and_shows_freshness():
    source = Path(__file__).with_name("weekly_inventory_report.html").read_text(
        encoding="utf-8"
    )

    assert "const WEEKLY_REPORT_AUTO_REFRESH_MS = 60 * 1000;" in source
    assert "if (background && reportActionInProgress)" in source
    assert "if (reportLoadPromise) return reportLoadPromise;" in source
    assert "loadWeeklyReport({background: true});" in source
    assert "window.setInterval(autoRefreshWeeklyReport" in source
    assert "document.addEventListener('visibilitychange'" in source
    assert "if (!document.hidden) autoRefreshWeeklyReport();" in source
    assert "Updated ${updatedTime} CT" in source