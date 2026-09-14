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


def test_mobile_lot_inventory_controls_do_not_force_horizontal_overflow():
    assert "@media (max-width: 700px)" in HTML
    assert ".lot-tab-bar {" in HTML
    assert "flex-direction: column;" in HTML
    assert ".lot-inventory-filter {" in HTML
    assert "min-width: 0;" in HTML


def test_lot_card_actions_stay_on_one_row_on_narrow_screens():
    assert "flex: 1 1 100%;" not in HTML
    assert "flex: 1 1 0;" in HTML


def test_lot_card_actions_have_distinct_visual_cues():
    assert "lot-action-correct" in HTML
    assert "lot-action-edit" in HTML
    assert "lot-action-delete" in HTML
    assert '<span aria-hidden="true">↕</span> Correct' in HTML
    assert '<span aria-hidden="true">✎</span> Edit' in HTML
    assert '<span aria-hidden="true">×</span> Delete' in HTML


def test_assignment_actions_have_distinct_visual_cues():
    assert "assignment-action-deactivate" in HTML
    assert "assignment-action-activate" in HTML
    assert "assignment-action-edit" in HTML
    assert "assignment-action-deactivate" in HTML
    assert "assignment-action-edit" in HTML