"""Listener interfaces for order related functions."""
import abc

from ibpy_native import models
from ibpy_native.interfaces.listeners import base

class OrderEventsListener(base.BaseListener):
    """Interface of listener for order related events."""
    @abc.abstractmethod
    def on_warning(self, order_id: int, msg: str):
        """Callback on event of order warning message received from IB.

        Args:
            order_id (int): The order's client identifier.
            msg (str): The warning message.
        """
        return NotImplemented

    @abc.abstractmethod
    def on_cancelled(self, order: models.OpenOrder):
        """Callback on event of order cancelation confirmed by IB.

        Args:
            order (:obj:`ibpy_native.models.OpenOrder`): The cancelled order.
        """
        return NotImplemented

    @abc.abstractmethod
    def on_rejected(self, order: models.OpenOrder, reason: str):
        """Callback on event of order rejected by IB.

        Args:
            order (:obj:`ibpy_native.models.OpenOrder`): The rejected order.
            reason (str): Reason of order rejection.
        """
        return NotImplemented

    @abc.abstractmethod
    def on_filled(self, order: models.OpenOrder):
        """Callback on event of order has been completely filled.

        Args:
            order (:obj:`ibpy_native.models.OpenOrder`): The completed order.
        """
        return NotImplemented
