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
        "Pallet Breakdown",
        "52-Week Avg",
        "Days Left",
    ):
        assert f">{heading}</th>" in compose