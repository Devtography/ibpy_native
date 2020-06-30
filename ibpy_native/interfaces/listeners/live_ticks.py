"""
Listener interfaces for live market data related functions.
"""

import abc
from typing import Union

from ibapi.wrapper import (HistoricalTick, HistoricalTickLast,
                           HistoricalTickBidAsk)
from ibpy_native.error import IBError

class LiveTicksListener(metaclass=abc.ABCMeta):
    """
    Interface of listener for "Tick-by-Tick Data" related functions.
    """
    @abc.abstractmethod
    def on_tick_receive(self, req_id: int, tick: Union[
            HistoricalTick, HistoricalTickLast, HistoricalTickBidAsk
        ]):
        """
        Callback when receives new live tick records.
        """
        return NotImplemented

    @abc.abstractmethod
    def on_error(self, err: IBError):
        """
        Callback when encounters errors.
        """
        return NotImplemented
