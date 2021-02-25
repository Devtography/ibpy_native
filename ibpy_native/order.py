"""IB order related resources."""
import threading
import queue
from typing import Dict, Optional

from ibapi import common
from ibapi import contract as ib_contract
from ibapi import order as ib_order
from ibapi import order_state as ib_order_state

from ibpy_native import error
from ibpy_native import models
from ibpy_native.interfaces import delegates
from ibpy_native.interfaces import listeners
from ibpy_native.utils import datatype
from ibpy_native.utils import finishable_queue as fq

class OrdersManager(delegates.OrdersManagementDelegate):
    """Class to handle orders related events."""
    def __init__(self,
                 event_listener: Optional[listeners.OrderEventsListener]=None):
        # Internal members
        self._lock = threading.Lock()
        self._listener = event_listener
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

    def is_pending_order(self, order_id: int) -> bool:
        if order_id in self._pending_queues:
            if self._pending_queues[order_id].status is fq.Status.INIT:
                return True

        return False

    #region - Internal functions
    def update_next_order_id(self, order_id: int):
        with self._lock:
            self._next_order_id = order_id

    def get_pending_queue(self, order_id: int) -> Optional[fq.FinishableQueue]:
        if order_id in self._pending_queues:
            return self._pending_queues[order_id]

        return None

    #region - Order events
    def order_error(self, err: error.IBError):
        if err.err_code == 399: # Warning message only
            if self._listener:
                self._listener.on_warning(order_id=err.rid, msg=err.msg)
            return
        if err.rid in self._pending_queues:
            if self._listener:
                self._listener.on_err(err)

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
            if (self._listener
                and order_state.status == "Filled"
                and order_state.commission != common.UNSET_DOUBLE):
                # Commission validation is to filter out the 1st incomplete
                # order filled status update.
                self._listener.on_filled(order=self._open_orders[order.orderId])
        else:
            self._open_orders[order.orderId] = models.OpenOrder(
                contract, order, order_state
            )
            if order.orderId in self._pending_queues:
                self._pending_queues[order.orderId].put(
                    element=fq.Status.FINISHED)

    def on_order_status_updated(
        self, order_id: int, status: str, filled: float, remaining: float,
        avg_fill_price: float, last_fill_price: float, mkt_cap_price: float
    ):
        if order_id in self._open_orders:
            self._open_orders[order_id].order_status_update(
                status=datatype.OrderStatus(status), filled=filled,
                remaining=remaining, avg_fill_price=avg_fill_price,
                last_fill_price=last_fill_price, mkt_cap_price=mkt_cap_price
            )

            if self._listener and status == "Cancelled":
                self._listener.on_cancelled(order=self._open_orders[order_id])

    def on_order_rejected(self, order_id: int, reason: str):
        if self._listener and order_id in self._open_orders:
            self._listener.on_rejected(order=self._open_orders[order_id],
                                       reason=reason)
    #endregion - Order events
    #endregion - Internal functions
