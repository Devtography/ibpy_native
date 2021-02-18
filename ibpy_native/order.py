"""IB order related resources."""
import threading

from ibpy_native.interfaces import delegates

class OrdersManager(delegates.OrdersManagementDelegate):
    """Class to handle orders related events.

    Args:
        account_manager: The accounts manager.
    """
    def __init__(self):
        # Internal members
        self._lock = threading.Lock()
        # Property
        self._next_order_id = 0

    @property
    def next_order_id(self) -> int:
        return self._next_order_id

    def update_next_order_id(self, order_id: int):
        with self._lock:
            self._next_order_id = order_id
