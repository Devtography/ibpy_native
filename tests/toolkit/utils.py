"""Utilities for making unittests easier to write."""
import asyncio
from typing import List, Union

from ibapi import wrapper as ib_wrapper

from ibpy_native import error
from ibpy_native.interfaces import listeners

def async_test(fn):
    # pylint: disable=invalid-name
    """Decorator for testing the async functions."""
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()

        return loop.run_until_complete(fn(*args, **kwargs))

    return wrapper

class MockLiveTicksListener(listeners.LiveTicksListener):
    """Mock notification listener"""
    ticks: List[Union[ib_wrapper.HistoricalTick,
                      ib_wrapper.HistoricalTickBidAsk,
                      ib_wrapper.HistoricalTickLast]] = []

    finished: bool = False

    def on_tick_receive(self, req_id: int,
                        tick: Union[ib_wrapper.HistoricalTick,
                                    ib_wrapper.HistoricalTickBidAsk,
                                    ib_wrapper.HistoricalTickLast]):
        print(tick)
        self.ticks.append(tick)

    def on_finish(self, req_id: int):
        self.finished = True

    def on_err(self, err: error.IBError):
        raise err
