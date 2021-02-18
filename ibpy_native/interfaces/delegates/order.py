"""Internal delegate module for orders related features."""
import abc

from ibpy_native import error

class OrdersManagementDelegate(metaclass=abc.ABCMeta):
    """Internal delegate protocol for handling orders."""
    @property
    @abc.abstractmethod
    def next_order_id(self) -> int:
        """int: Next valid order ID. If is `0`, it means the connection
        with IB has not been established yet.
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
