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

def no_transmit(order_id: int) -> ib_order.Order:
    """Market order with `transmit` set to `False`."""
    order = _base_order(order_id, datatype.OrderAction.BUY)
    order.orderType = "MKT"
    order.transmit = False

    return order
