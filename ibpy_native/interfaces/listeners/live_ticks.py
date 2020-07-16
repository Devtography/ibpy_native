"""Listener interfaces for live market data related functions."""

import abc
from typing import Union

from ibapi.wrapper import (HistoricalTick, HistoricalTickBidAsk,
                           HistoricalTickLast)

from .base import BaseListener

class LiveTicksListener(BaseListener):
    """Interface of listener for "Tick-by-Tick Data" related functions."""
    @abc.abstractmethod
    def on_tick_receive(self, req_id: int, tick: Union[
            HistoricalTick, HistoricalTickBidAsk, HistoricalTickLast
        ]):
        """Callback on receives new live tick records.

        Args:
            req_id (int): Request identifier (or ticker ID in IB API).
            tick (Union[HistoricalTick, HistoricalTickBidAsk,
                HistoricalTickLast]): Tick data received.
        """
        return NotImplemented

    @abc.abstractmethod
    def on_finish(self, req_id: int):
        """Callback on `FINISHED` status is received.

        Args:
            req_id (int): Request identifier (or ticker ID in IB API).
        """
        return NotImplemented
