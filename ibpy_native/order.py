"""IB order related resources."""
import threading
import queue
from typing import Dict, Optional

from ibapi import contract as ib_contract
from ibapi import order as ib_order
from ibapi import order_state as ib_order_state

from ibpy_native import error
from ibpy_native import models
from ibpy_native.interfaces import delegates
from ibpy_native.utils import finishable_queue as fq

class OrdersManager(delegates.OrdersManagementDelegate):
    """Class to handle orders related events."""
    def __init__(self):
        # Internal members
        self._lock = threading.Lock()
        # Property
        self._next_order_id = 0
        self._open_orders: Dict[int, models.OpenOrder] = {}
        self._pending_queues: Dict[int, fq.FinishableQueue] = {}

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
        return val in self._pending_queues

    #region - Internal functions
    def get_pending_queue(self, order_id: int) -> Optional[fq.FinishableQueue]:
        if order_id in self._pending_queues:
            return self._pending_queues[order_id]

        return None

    #region - Order events
    def order_error(self, err: error.IBError):
        if err.err_code == 399: # Warning message only
            return
        if err.rid in self._pending_queues:
            # Signals the order submission error
            if self._pending_queues[err.rid].status is not fq.Status.FINISHED:
                self._pending_queues[err.rid].put(element=err)

    def on_order_submission(self, order_id: int):
        """INTERNAL FUNCTION! Creates a new `FinishableQueue` with `order_id`
        as key in `_pending_queues` for order submission task completeion
        status monitoring.

        Args:
            order_id (int): The order's identifier on TWS/Gateway.

        Raises:
            ibpy_native.error.IBError: If existing `FinishableQueue` assigned
                for the `order_id` specificed is found.
        """
        if order_id not in self._pending_queues:
            self._pending_queues[order_id] = fq.FinishableQueue(
                queue_to_finish=queue.Queue()
            )
        else:
            raise error.IBError(
                rid=order_id, err_code=error.IBErrorCode.DUPLICATE_ORDER_ID,
                err_str=f"Existing queue assigned for order ID {order_id} "
                        "found. Possiblely duplicate order ID is being used."
            )

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
            if order.orderId in self._pending_queues:
                self._pending_queues[order.orderId].put(
                    element=fq.Status.FINISHED)

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
    #endregion - Order events
    #endregion - Internal functions
