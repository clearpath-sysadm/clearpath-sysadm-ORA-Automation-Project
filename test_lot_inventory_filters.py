"""Regression coverage for lot inventory visibility filters."""

from pathlib import Path


HTML = (Path(__file__).resolve().parent / "lot_inventory.html").read_text()


def test_lot_inventory_defaults_to_in_stock():
    assert 'let lotInventoryFilter = \'in-stock\';' in HTML
    assert '<option value="in-stock" selected>In Stock</option>' in HTML
    assert "return balance > 0;" in HTML


def test_lot_inventory_retains_all_requested_views():
    assert '<option value="all">All Lots</option>' in HTML
    assert '<option value="active">Active</option>' in HTML
    assert '<option value="non-depleted">Non-Depleted</option>' in HTML
    assert "if (lotInventoryFilter === 'all') return true;" in HTML
    assert "if (lotInventoryFilter === 'active') return status === 'active';" in HTML
    assert "if (lotInventoryFilter === 'non-depleted') return status !== 'depleted';" in HTML