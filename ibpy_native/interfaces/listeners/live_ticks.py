"""
Listener interfaces for live market data related functions.
"""

import abc

class LiveTicksListener(metaclass=abc.ABCMeta):
    """
    Interface of listener for "Tick-by-Tick Data" related functions.
    """
    @abc.abstractmethod
    def on_tick_receive(self, req_id: int, tick):
        """
        Callback when receives new live tick records.
        """
        return NotImplemented
