"""Utilities for making unittests easier to write."""
# pylint: disable=protected-access
import asyncio
import queue
from typing import Dict, List, Union

from ibapi import wrapper as ib_wrapper

from ibpy_native import error
from ibpy_native import models
from ibpy_native.interfaces import delegates
from ibpy_native.interfaces import listeners
from ibpy_native.utils import finishable_queue as fq

def async_test(fn):
    # pylint: disable=invalid-name
    """Decorator for testing the async functions."""
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()

        return loop.run_until_complete(fn(*args, **kwargs))

    return wrapper

class MockAccountManagementDelegate(delegates.AccountsManagementDelegate):
    """Mock accounts delegate"""
    def __init__(self):
        self._account_list: Dict[str, models.Account] = []
        self._account_updates_queue: fq.FinishableQueue = fq.FinishableQueue(
            queue_to_finish=queue.Queue()
        )

    @property
    def accounts(self) -> Dict[str, models.Account]:
        return self._account_list

    @property
    def account_updates_queue(self) -> fq.FinishableQueue:
        return self._account_updates_queue

    def on_account_list_update(self, account_list: List[str]):
        for account_id in account_list:
            self._account_list.append(models.Account(account_id))

    async def sub_account_updates(self, account: models.Account):
        pass

    async def unsub_account_updates(self):
        pass

class MockLiveTicksListener(listeners.LiveTicksListener):
    """Mock notification listener"""
    ticks: List[Union[ib_wrapper.HistoricalTick,
                      ib_wrapper.HistoricalTickBidAsk,
                      ib_wrapper.HistoricalTickLast]] = []

    finished: bool = False

    def on_tick_receive(self, req_id: int,
                        tick: Union[ib_wrapper.HistoricalTick,
                                    ib_wrapper.HistoricalTickBidAsk,
                                    ib_wrapper.HistoricalTickLast,]):
        print(tick)
        self.ticks.append(tick)

    def on_finish(self, req_id: int):
        self.finished = True

    def on_err(self, err: error.IBError):
        raise err
