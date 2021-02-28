"""Listener interfaces for connectivity status between the API client and
IB TWS/Gateway.
"""
import abc

class ConnectionListener(metaclass=abc.ABCMeta):
    """Interface of listener for connection between the API client and IB
    TWS/Gateway.
    """
    @abc.abstractmethod
    def on_connected(self):
        """Callback on connection is established."""
        return NotImplemented

    @abc.abstractmethod
    def on_disconnected(self):
        """Callback on connection is dropped."""
        return NotImplemented
