"""Tests for safe ShipStation promo-order assignee reconciliation."""

from unittest.mock import patch

from src.lot_tagger.tagger import reconcile_promo_order_assignees
from src.services.shipstation.api_client import assign_user_to_order


PROMO_MAP = {'17613': '17612', '17905': '17904'}
VARIANT_MAP = {
    '17612-1': {'base_sku': '17612', 'unit_multiplier': 1},
    '17904-1': {'base_sku': '17904', 'unit_multiplier': 1},
}


def order(order_id, order_key, sku, user_id=None, status='awaiting_shipment'):
    return {
        'orderId': order_id,
        'orderKey': order_key,
        'orderNumber': f'ORDER-{order_key}',
        'orderStatus': status,
        'userId': user_id,
        'items': [{'sku': sku, 'quantity': 1}],
    }


def test_assigns_both_promo_families_from_matching_variant_siblings():
    orders = [
        order(1, 'A', '17612-1', 41),
        order(2, 'A', '17613'),
        order(3, 'B', '17904-1', 52),
        order(4, 'B', '17905'),
    ]
    with patch(
        'src.lot_tagger.tagger.assign_user_to_order',
        return_value={'success': True},
    ) as assign:
        result = reconcile_promo_order_assignees(orders, PROMO_MAP, VARIANT_MAP)

    assert result['assigned'] == 2
    assert assign.call_args_list[0].args == (2, 41)
    assert assign.call_args_list[1].args == (4, 52)
    assert orders[1]['userId'] == 41
    assert orders[3]['userId'] == 52


def test_does_not_overwrite_an_existing_assignee():
    orders = [
        order(1, 'A', '17612-1', 41),
        order(2, 'A', '17613', 99),
    ]
    with patch('src.lot_tagger.tagger.assign_user_to_order') as assign:
        result = reconcile_promo_order_assignees(orders, PROMO_MAP, VARIANT_MAP)

    assign.assert_not_called()
    assert result['already_assigned'] == 1
    assert orders[1]['userId'] == 99


def test_leaves_promo_unassigned_without_matching_base_sibling():
    orders = [order(2, 'A', '17613')]
    with patch('src.lot_tagger.tagger.assign_user_to_order') as assign:
        result = reconcile_promo_order_assignees(orders, PROMO_MAP, VARIANT_MAP)

    assign.assert_not_called()
    assert result['missing_match'] == 1


def test_leaves_promo_unassigned_when_base_assignees_conflict():
    orders = [
        order(1, 'A', '17612-1', 41),
        order(2, 'A', '17612', 52),
        order(3, 'A', '17613'),
    ]
    with patch('src.lot_tagger.tagger.assign_user_to_order') as assign:
        result = reconcile_promo_order_assignees(orders, PROMO_MAP, VARIANT_MAP)

    assign.assert_not_called()
    assert result['ambiguous_match'] == 1


def test_api_failure_is_reported_and_repeat_run_can_retry():
    orders = [
        order(1, 'A', '17612-1', 41),
        order(2, 'A', '17613'),
    ]
    with patch(
        'src.lot_tagger.tagger.assign_user_to_order',
        side_effect=[
            {'success': False, 'error': 'temporary failure'},
            {'success': True},
        ],
    ) as assign:
        first = reconcile_promo_order_assignees(orders, PROMO_MAP, VARIANT_MAP)
        second = reconcile_promo_order_assignees(orders, PROMO_MAP, VARIANT_MAP)

    assert first['errors'] == 1
    assert second['assigned'] == 1
    assert assign.call_count == 2
    assert orders[1]['userId'] == 41


def test_ignores_non_awaiting_orders_and_does_not_cross_order_keys():
    orders = [
        order(1, 'A', '17612-1', 41),
        order(2, 'B', '17613'),
        order(3, 'A', '17613', status='shipped'),
    ]
    with patch('src.lot_tagger.tagger.assign_user_to_order') as assign:
        result = reconcile_promo_order_assignees(orders, PROMO_MAP, VARIANT_MAP)

    assign.assert_not_called()
    assert result['missing_match'] == 1


def test_assignment_api_uses_dedicated_endpoint_and_minimal_payload():
    response = type('Response', (), {'status_code': 200})()
    with patch(
        'src.services.shipstation.api_client.get_shipstation_credentials',
        return_value=('key', 'secret'),
    ), patch(
        'src.services.shipstation.api_client.fetch_order_by_id',
        return_value={
            'success': True,
            'order': {'orderStatus': 'awaiting_shipment', 'userId': None},
        },
    ), patch(
        'src.services.shipstation.api_client.get_shipstation_headers',
        return_value={'Authorization': 'redacted'},
    ), patch(
        'src.services.shipstation.api_client.requests.post',
        return_value=response,
    ) as request:
        result = assign_user_to_order(123, 41)

    assert result == {'success': True, 'assigned': True}
    assert request.call_args.args[0].endswith('/orders/assignuser')
    assert request.call_args.kwargs['json'] == {
        'orderIds': [123],
        'userId': 41,
    }


def test_assignment_api_rechecks_and_preserves_new_operator_assignment():
    with patch(
        'src.services.shipstation.api_client.get_shipstation_credentials',
        return_value=('key', 'secret'),
    ), patch(
        'src.services.shipstation.api_client.fetch_order_by_id',
        return_value={
            'success': True,
            'order': {'orderStatus': 'awaiting_shipment', 'userId': 99},
        },
    ), patch('src.services.shipstation.api_client.requests.post') as request:
        result = assign_user_to_order(123, 41)

    request.assert_not_called()
    assert result == {
        'success': True,
        'assigned': False,
        'reason': 'already_assigned',
        'user_id': 99,
    }