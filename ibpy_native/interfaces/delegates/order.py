"""Internal delegate module for orders related features."""
import abc

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
