"""Utilities for making unittests easier to write."""
# pylint: disable=protected-access
import asyncio
from typing import List, Union

from ibapi import wrapper as ib_wrapper

from ibpy_native import account
from ibpy_native import error
from ibpy_native.interfaces import delegates
from ibpy_native.interfaces import listeners

def async_test(fn):
    # pylint: disable=invalid-name
    """Decorator for testing the async functions."""
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()

        return loop.run_until_complete(fn(*args, **kwargs))

    return wrapper

class MockAccountListDelegate(delegates._AccountListDelegate):
    """Mock accounts delegate"""

    _account_list: List[account.Account] = []

    @property
    def accounts(self) -> List[account.Account]:
        return self._account_list

    def on_account_list_update(self, account_list: List[str]):
        # self._account_list = account_list
        for account_id in account_list:
            self._account_list.append(account.Account(account_id))

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
