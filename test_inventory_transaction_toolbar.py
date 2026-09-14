"""Regression coverage for Transaction Log toolbar hierarchy."""

from pathlib import Path


HTML = (Path(__file__).resolve().parent / "inventory_transactions.html").read_text()


def test_filter_and_action_controls_are_visually_grouped():
    assert 'aria-label="Transaction filters"' in HTML
    assert 'aria-label="Transaction actions"' in HTML
    assert '<span class="transaction-toolbar-label">Filters</span>' in HTML
    assert '<span class="transaction-toolbar-label">Actions</span>' in HTML


def test_primary_toolbar_actions_have_distinct_styles():
    assert 'class="btn btn-filter"' in HTML
    assert 'class="btn btn-clear"' in HTML
    assert 'class="btn btn-add-transaction"' in HTML
    assert 'class="btn btn-view-balances"' in HTML


def test_mobile_transaction_cards_use_scannable_sections():
    assert 'class="transaction-card-details"' in HTML
    assert HTML.count('class="transaction-card-field"') == 3
    assert 'class="transaction-card-notes"' in HTML