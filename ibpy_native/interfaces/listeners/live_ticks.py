"""Listener interfaces for live market data related functions."""
# pylint: disable=protected-access
import abc
from typing import Union

from ibapi import wrapper

from ibpy_native.interfaces.listeners import base

class LiveTicksListener(base.BaseListener):
    """Interface of listener for "Tick-by-Tick Data" related functions."""
    @abc.abstractmethod
    def on_tick_receive(self, req_id: int, tick: Union[
            wrapper.HistoricalTick, wrapper.HistoricalTickBidAsk,
            wrapper.HistoricalTickLast,
        ]):
        """Callback on receives new live tick records.

        Args:
            req_id (int): Request identifier (or ticker ID in IB API).
            tick (:obj:`Union[ibapi.wrapper.HistoricalTick,
                ibapi.wrapper.HistoricalTickBidAsk,
                ibapi.wrapper.HistoricalTickLast]`): Tick data received.
        """
        return NotImplemented

    @abc.abstractmethod
    def on_finish(self, req_id: int):
        """Callback on `FINISHED` status is received.

        Args:
            req_id (int): Request identifier (or ticker ID in IB API).
        """
        return NotImplemented
