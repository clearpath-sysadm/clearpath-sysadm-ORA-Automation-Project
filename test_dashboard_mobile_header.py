from pathlib import Path


def test_mobile_dashboard_header_gives_timestamp_its_own_row():
    html = Path(__file__).with_name("index.html").read_text(encoding="utf-8")

    assert "@media (max-width: 600px)" in html
    assert "grid-template-columns: minmax(0, 1fr) auto;" in html
    assert ".top-bar-actions .last-updated" in html
    assert "grid-column: 1 / -1;" in html
    assert "white-space: nowrap;" in html


def test_narrow_header_keeps_controls_accessible():
    html = Path(__file__).with_name("index.html").read_text(encoding="utf-8")

    assert "@media (max-width: 380px)" in html
    assert 'id="refresh-btn"' in html
    assert 'aria-label="Toggle dark mode"' in html
    assert "#refresh-btn svg" in html
    assert "min-height: 44px;" in html