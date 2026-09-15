from pathlib import Path


def test_single_lot_mobile_card_keeps_label_and_number_inline():
    html = Path(__file__).with_name("shipment_summary.html").read_text(
        encoding="utf-8"
    )

    assert 'class="summary-card-lot-single-line"' in html
    assert '<span class="summary-card-lots-label">Lot</span>' in html
    assert '<span class="summary-card-lot-single">${lotName}${eolBadge}</span>' in html
    assert ".summary-card-lot-single-line {" in html
    assert "display: flex;" in html