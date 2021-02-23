"""IB order related resources."""
import threading
from typing import Dict

from ibapi import contract as ib_contract
from ibapi import order as ib_order
from ibapi import order_state as ib_order_state

from ibpy_native import error
from ibpy_native import models
from ibpy_native.interfaces import delegates

class OrdersManager(delegates.OrdersManagementDelegate):
    """Class to handle orders related events."""
    def __init__(self):
        # Internal members
        self._lock = threading.Lock()
        # Property
        self._next_order_id = 0
        self._open_orders: Dict[int, models.OpenOrder] = {}

    @property
    def next_order_id(self) -> int:
        return self._next_order_id

    @property
    def open_orders(self) -> Dict[int, models.OpenOrder]:
        return self._open_orders

    def update_next_order_id(self, order_id: int):
        with self._lock:
            self._next_order_id = order_id

    def is_pending_order(self, val: int) -> bool:
        return False

    def order_error(self, err: error.IBError):
        if err.err_code == 399: # Warning message only
            return

    def on_open_order_updated(
        self, contract: ib_contract.Contract, order: ib_order.Order,
        order_state: ib_order_state.OrderState
    ):
        if order.orderId in self._open_orders:
            self._open_orders[order.orderId].order_update(order, order_state)
        else:
            self._open_orders[order.orderId] = models.OpenOrder(
                contract, order, order_state
            )

    def on_order_status_updated(
        self, order_id: int, filled: float, remaining: float,
        avg_fill_price: float, last_fill_price: float, mkt_cap_price: float
    ):
        if order_id in self._open_orders and filled != 0:
            # Filter out the message(s) with no actual trade
            self._open_orders[order_id].order_status_update(
                filled, remaining, avg_fill_price,
                last_fill_price, mkt_cap_price
            )
