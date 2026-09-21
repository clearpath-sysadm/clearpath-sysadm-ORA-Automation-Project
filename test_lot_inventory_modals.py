import re
from pathlib import Path


HTML = (Path(__file__).resolve().parent / "lot_inventory.html").read_text()


def test_lot_inventory_overlays_use_visible_dialog_container():
    for modal_id in ("sku-lot-modal", "lot-modal", "correction-modal"):
        overlay = re.search(
            rf'<div class="modal-overlay" id="{modal_id}">\s*'
            r'<div class="([^"]+)">',
            HTML,
        )
        assert overlay, f"{modal_id} overlay or inner dialog is missing"
        assert "modal-dialog" in overlay.group(1).split()
        assert "modal" not in overlay.group(1).split()


def test_add_lot_and_related_dialogs_keep_open_close_hooks():
    assert 'onclick="openAddModal()"' in HTML
    assert "document.getElementById('lot-modal').classList.add('active')" in HTML
    assert "document.getElementById('lot-modal').classList.remove('active')" in HTML

    assert "document.getElementById('correction-modal').classList.add('active')" in HTML
    assert "document.getElementById('correction-modal').classList.remove('active')" in HTML

    assert "document.getElementById('sku-lot-modal').classList.add('active')" in HTML
    assert "document.getElementById('sku-lot-modal').classList.remove('active')" in HTML