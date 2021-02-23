"""Internal delegate module for orders related features."""
import abc
from typing import Dict

from ibapi import contract as ib_contract
from ibapi import order as ib_order
from ibapi import order_state as ib_order_state

from ibpy_native import error
from ibpy_native import models

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
    def update_next_order_id(self, order_id: int):
        """Internal function to update the next order ID stored. Not expected
        to be invoked by the user.

        Args:
            order_id (int): The updated order identifier.
        """
        return NotImplemented

    @abc.abstractmethod
    def is_pending_order(self, val: int) -> bool:
        """Check if a identifier matches with an existing order in pending.

        Args:
            val (int): The value to validate.

        Returns:
            bool: `True` if `val` matches with the order identifier of an
                pending order. `False` if otherwise.
        """
        return NotImplemented

    @abc.abstractmethod
    def order_error(self, err: error.IBError):
        """Handles the error return from IB for the order submiteted."""
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
        self, order_id: int, filled: float, remaining: float,
        avg_fill_price: float, last_fill_price: float, mkt_cap_price: float
    ):
        """INTERNAL FUNCTION! Handles the `orderStatus` callback from IB.

        Args:
            order_id (int): The order's identifier on TWS/Gateway.
            filled (float): Number of filled positions.
            remaining (float): The remnant positions.
        """
        return NotImplemented
