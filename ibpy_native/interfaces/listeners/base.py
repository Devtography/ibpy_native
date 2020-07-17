"""Listener interfaces for general purposes."""
import abc

from ibpy_native.error import IBError

class BaseListener(metaclass=abc.ABCMeta):
    """Interface of listener for general purposes."""
    @abc.abstractmethod
    def on_err(self, err: IBError):
        """Callback when encounters errors."""
        return NotImplemented
