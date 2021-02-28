"""Internal delegate module for orders related features."""
import abc
from typing import Dict, Optional

from ibapi import contract as ib_contract
from ibapi import order as ib_order
from ibapi import order_state as ib_order_state

from ibpy_native import error
from ibpy_native import models
from ibpy_native.utils import finishable_queue as fq

class OrdersManagementDelegate(metaclass=abc.ABCMeta):
    """Internal delegate protocol for handling orders."""
    @property
    @abc.abstractmethod
    def next_order_id(self) -> int:
        """int: Next valid order ID. If is `0`, it means the connection
        with IB has not been established yet.
        """
        return NotImplemented

    @property
    @abc.abstractmethod
    def open_orders(self) -> Dict[int, models.OpenOrder]:
        """:obj:`Dict[int, models.OpenOrder]`: Open orders returned from IB
        during this session.
        """
        return NotImplemented

    @abc.abstractmethod
    def is_pending_order(self, order_id: int) -> bool:
        """Check if a identifier matches with an existing order in pending.

        Args:
            order_id (int): The order identifier to validate.

        Returns:
            bool: `True` if `val` matches with the order identifier of an
                pending order. `False` if otherwise.
        """
        return NotImplemented

    #region - Internal functions
    @abc.abstractmethod
    def update_next_order_id(self, order_id: int):
        """INTERNAL FUNCTION! Update the next order ID stored.

        Args:
            order_id (int): The updated order identifier.
        """
        return NotImplemented

    @abc.abstractmethod
    def get_pending_queue(self, order_id: int) -> Optional[fq.FinishableQueue]:
        """INTERNAL FUNCTION! Retrieve the queue for order submission task
        completeion status.

        Args:
            order_id (int): The order's identifier on TWS/Gateway.

        Returns:
            :obj:`Optional[ibpy_native.utils.finishable_queue.FinishableQueue]`:
                Queue to monitor for the completeion signal of the order
                submission task. `None` should be return if the `order_id`
                passed in does not match with any queue stored.
        """
        return NotImplemented

    #region - Order events
    @abc.abstractmethod
    def order_error(self, err: error.IBError):
        """INTERNAL FUNCTION! Handles the error return from IB for the order
        submiteted.

        Args:
            err (:obj:`ibpy_native.error.IBError`): Error returned from IB.
        """
        return NotImplemented

    @abc.abstractmethod
    def on_order_submission(self, order_id: int):
        """INTERNAL FUNCTION! Triggers while invoking the internal order
        submission function.

        Args:
            order_id (int): The order's identifier on TWS/Gateway.
        """
        return NotImplemented

    @abc.abstractmethod
    def on_open_order_updated(
        self, contract: ib_contract.Contract, order: ib_order.Order,
        order_state: ib_order_state.OrderState
    ):
        """INTERNAL FUNCTION! Handles the open order returned from IB
        after an order is submitted to TWS/Gateway.

        Args:
            contract (:obj:`ibapi.contract.Contract`): The order's contract.
            order (:obj:`ibapi.order.Order`): The current active order returned
                from IB.
            order_state (:obj:`ibapi.order_state.OrderState`): Order states/
                status returned from IB.
        """
        return NotImplemented

    @abc.abstractmethod
    def on_order_status_updated(
        self, order_id: int, status: str, filled: float, remaining: float,
        avg_fill_price: float, last_fill_price: float, mkt_cap_price: float
    ):
        """INTERNAL FUNCTION! Handles the `orderStatus` callback from IB.

        Args:
            order_id (int): The order's identifier on TWS/Gateway.
            status (str): The current status of the order.
            filled (float): Number of filled positions.
            remaining (float): The remnant positions.
            avg_fill_price (float): Average filling price.
            last_fill_price (float): Price at which the last positions were
                filled.
            mkt_cap_price (float): If an order has been capped, this indicates
                the current capped price.
        """
        return NotImplemented

    @abc.abstractmethod
    def on_order_rejected(self, order_id: int, reason: str):
        """INTERNAL FUNCTION! Handles the order rejection error and message
        received in `error` callback from IB.

        Args:
            order_id (int): The order's client identifier.
            reason (str): Reason of order rejection.
        """
        return NotImplemented
    #endregion - Order events

    @abc.abstractmethod
    def on_disconnected(self):
        """INTERNAL FUNCTION! Handles the event of API connection dropped.
        """
        return NotImplemented
    #endregion - Internal functions
