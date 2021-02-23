"""Predefined orders for unittest."""
from ibapi import order as ib_order

from ibpy_native.utils import datatype

def _base_order(order_id: int, action: datatype.OrderAction) -> ib_order.Order:
    order = ib_order.Order()
    order.orderId = order_id
    order.action = action.value
    order.totalQuantity = 100

    return order

def lmt(order_id: int, action: datatype.OrderAction,
        price: float) -> ib_order.Order:
    """Limit order"""
    order = _base_order(order_id, action)
    order.orderType = "LMT"
    order.lmtPrice = price

    return order

def mkt(order_id: int, action: datatype.OrderAction) -> ib_order.Order:
    """Market order"""
    order = _base_order(order_id, action)
    order.orderType = "MKT"

    return order
