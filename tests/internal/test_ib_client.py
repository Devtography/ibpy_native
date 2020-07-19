"""Unit tests for module `ibpy_native.client`."""
import asyncio
import enum
import os
import threading
import unittest

from datetime import datetime
from typing import List, Union

import pytz

from ibapi.contract import Contract
from ibapi.wrapper import (
    HistoricalTick, HistoricalTickBidAsk, HistoricalTickLast
)
from ibpy_native.error import IBError
from ibpy_native.interfaces.listeners import LiveTicksListener
from ibpy_native.internal.client import IBClient
from ibpy_native.internal.wrapper import IBWrapper
from ibpy_native.utils import finishable_queue as fq
from tests.utils import async_test

class _MockLiveTicksListener(LiveTicksListener):
    """Mock live ticks listener for unit test."""
    ticks: List[Union[
        HistoricalTick, HistoricalTickBidAsk, HistoricalTickLast
    ]] = []
    finished: bool = False

    def on_tick_receive(self, req_id: int, tick: Union[
            HistoricalTick, HistoricalTickBidAsk, HistoricalTickLast
        ]):
        print(tick)
        self.ticks.append(tick)

    def on_finish(self, req_id: int):
        self.finished = True

    def on_err(self, err: IBError):
        raise err

class Const(enum.IntEnum):
    """Predefined request IDs for tests in `TestIBClient`."""
    RID_RESOLVE_CONTRACT = 43
    RID_RESOLVE_HEAD_TIMESTAMP = 14001
    RID_RESOLVE_HEAD_TIMESTAMP_EPOCH = 14002
    RID_FETCH_HISTORICAL_TICKS = 18001
    RID_FETCH_HISTORICAL_TICKS_ERR = 18002
    RID_STREAM_LIVE_TICKS = 19001
    RID_CANCEL_LIVE_TICKS_STREAM = 19002

class TestIBClient(unittest.TestCase):
    """Unit tests for class `IBClient`."""
    __contract = Contract()
    __contract.secType = 'CASH'
    __contract.symbol = 'EUR'
    __contract.exchange = 'IDEALPRO'
    __contract.currency = 'GBP'

    @classmethod
    def setUpClass(cls):
        IBClient.TZ = pytz.timezone('America/New_York')

        cls.wrapper = IBWrapper()
        cls.client = IBClient(cls.wrapper)

        cls.client.connect(
            os.getenv('IB_HOST', '127.0.0.1'),
            int(os.getenv('IB_PORT', '4002')),
            1001
        )

        thread = threading.Thread(target=cls.client.run)
        thread.start()

        setattr(cls.client, "_thread", thread)

    def test_resolve_contract(self):
        """
        Test function `resolve_contract`.
        """
        contract = Contract()
        contract.secType = "FUT"
        contract.lastTradeDateOrContractMonth = "202006"
        contract.symbol = "MYM"
        contract.exchange = "ECBOT"

        resolved_contract = self.client.resolve_contract(
            Const.RID_RESOLVE_CONTRACT.value, contract
        )

        self.assertIsNotNone(resolved_contract)
        print(resolved_contract)

    def test_resolve_head_timestamp(self):
        """Test function `resolve_head_timestamp`."""
        resolved_contract = self.client.resolve_contract(
            Const.RID_RESOLVE_CONTRACT.value, self.__contract
        )

        print(resolved_contract)

        head_timestamp = self.client.resolve_head_timestamp(
            Const.RID_RESOLVE_HEAD_TIMESTAMP.value, resolved_contract
        )

        print(head_timestamp)

        self.assertIsNotNone(head_timestamp)
        self.assertIsInstance(head_timestamp, int)

    def test_fetch_historical_ticks(self):
        """Test function `fetch_historical_ticks`."""
        timeout = 60

        resolved_contract = self.client.resolve_contract(
            Const.RID_RESOLVE_CONTRACT.value, self.__contract
        )

        data = self.client.fetch_historical_ticks(
            Const.RID_FETCH_HISTORICAL_TICKS.value, resolved_contract,
            start=IBClient.TZ.localize(
                datetime(2020, 4, 29, 10, 30, 0)
            ),
            end=IBClient.TZ.localize(
                datetime(2020, 4, 29, 10, 31, 0)
            ),
            show='MIDPOINT', timeout=timeout
        )

        self.assertIsInstance(data[0], list)
        self.assertTrue(data[1], True)
        self.assertGreater(len(data[0]), 0)
        self.assertIsInstance(data[0][0], HistoricalTick)

        data = self.client.fetch_historical_ticks(
            Const.RID_FETCH_HISTORICAL_TICKS.value, resolved_contract,
            start=IBClient.TZ.localize(
                datetime(2020, 4, 29, 10, 30, 0)
            ),
            end=IBClient.TZ.localize(
                datetime(2020, 4, 29, 10, 31, 0)
            ),
            show='BID_ASK', timeout=timeout
        )

        self.assertIsInstance(data[0], list)
        self.assertTrue(data[1], True)
        self.assertGreater(len(data[0]), 0)
        self.assertIsInstance(data[0][0], HistoricalTickBidAsk)

        data = self.client.fetch_historical_ticks(
            Const.RID_FETCH_HISTORICAL_TICKS.value, resolved_contract,
            start=IBClient.TZ.localize(
                datetime(2020, 4, 29, 10, 30, 0)
            ),
            end=IBClient.TZ.localize(
                datetime(2020, 4, 29, 10, 31, 0)
            ),
            timeout=timeout
        )

        self.assertIsInstance(data[0], list)
        self.assertTrue(data[1], True)
        self.assertGreater(len(data[0]), 0)
        self.assertIsInstance(data[0][0], HistoricalTickLast)

    def test_fetch_historical_ticks_err(self):
        """Test function `fetch_historical_ticks` for the error cases."""
        resolved_contract = self.client.resolve_contract(
            Const.RID_RESOLVE_CONTRACT.value, self.__contract
        )

        # Incorrect value of `show`
        with self.assertRaises(ValueError):
            self.client.fetch_historical_ticks(
                Const.RID_FETCH_HISTORICAL_TICKS_ERR.value, resolved_contract,
                datetime.now(), show='LAST'
            )

        # Timezone of start & end are not identical
        with self.assertRaises(ValueError):
            self.client.fetch_historical_ticks(
                Const.RID_FETCH_HISTORICAL_TICKS_ERR.value, resolved_contract,
                datetime.now().astimezone(pytz.timezone('Asia/Hong_Kong')),
                datetime.now().astimezone(pytz.timezone('America/New_York'))
            )

        # Invalid contract object
        with self.assertRaises(IBError):
            self.client.fetch_historical_ticks(
                Const.RID_FETCH_HISTORICAL_TICKS_ERR.value, Contract(),
                datetime(2020, 5, 20, 3, 20, 0).astimezone(IBClient.TZ),
                datetime.now().astimezone(IBClient.TZ)
            )

    @async_test
    async def test_stream_live_ticks(self):
        """Test function `stream_live_ticks`."""
        async def cancel_req():
            await asyncio.sleep(3)
            self.client.cancelTickByTickData(
                reqId=Const.RID_STREAM_LIVE_TICKS.value
            )

            queue = self.wrapper.get_request_queue(
                req_id=Const.RID_STREAM_LIVE_TICKS
            )
            queue.put(fq.Status.FINISHED)

        resolved_contract = self.client.resolve_contract(
            req_id=Const.RID_RESOLVE_CONTRACT.value, contract=self.__contract
        )

        listener = _MockLiveTicksListener()

        stream = asyncio.create_task(
            self.client.stream_live_ticks(
                req_id=Const.RID_STREAM_LIVE_TICKS.value,
                contract=resolved_contract,
                listener=listener,
                tick_type='BidAsk'
            )
        )
        cancel = asyncio.create_task(cancel_req())

        try:
            await stream
            await cancel
        except IBError as err:
            tasks = asyncio.all_tasks()
            for task in tasks:
                task.cancel()

            raise err

        self.assertGreater(len(listener.ticks), 0)
        self.assertTrue(listener.finished)

    @async_test
    async def test_cancel_live_ticks_stream(self):
        """Test function `cancel_live_ticks_stream`."""
        async def cancel_req():
            await asyncio.sleep(3)
            self.client.cancel_live_ticks_stream(
                req_id=Const.RID_CANCEL_LIVE_TICKS_STREAM.value
            )

        resolved_contract = self.client.resolve_contract(
            req_id=Const.RID_RESOLVE_CONTRACT.value, contract=self.__contract
        )

        listener = _MockLiveTicksListener()

        stream = asyncio.create_task(
            self.client.stream_live_ticks(
                req_id=Const.RID_CANCEL_LIVE_TICKS_STREAM.value,
                contract=resolved_contract,
                listener=listener,
                tick_type='BidAsk'
            )
        )
        cancel = asyncio.create_task(cancel_req())

        try:
            await stream
            await cancel
        except IBError as err:
            tasks = asyncio.all_tasks()
            for task in tasks:
                task.cancel()

            raise err

        self.assertTrue(listener.finished)

    @classmethod
    def tearDownClass(cls):
        cls.client.disconnect()
