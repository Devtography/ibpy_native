"""Unit tests for module `ibpy_native.client`."""
import asyncio
import datetime
import enum
import os
import threading
import unittest
from typing import List, Union

import pytz

from ibapi import contract as ib_contract
from ibapi import wrapper as ib_wrapper

from ibpy_native import error
from ibpy_native.interfaces import listeners
from ibpy_native.internal import client as ibpy_client
from ibpy_native.internal import wrapper as ibpy_wrapper
from ibpy_native.utils import finishable_queue as fq

from tests import utils

class _MockLiveTicksListener(listeners.LiveTicksListener):
    """Mock live ticks listener for unit test."""
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

class Const(enum.IntEnum):
    """Predefined request IDs for tests in `TestIBClient`."""
    RID_RESOLVE_CONTRACT = 43
    RID_RESOLVE_HEAD_TIMESTAMP = 14001
    RID_RESOLVE_HEAD_TIMESTAMP_EPOCH = 14002
    RID_FETCH_HISTORICAL_TICKS = 18001
    RID_FETCH_HISTORICAL_TICKS_ERR = 18002
    RID_STREAM_LIVE_TICKS = 19001
    RID_CANCEL_LIVE_TICKS_STREAM = 19002
    RID_CANCEL_LIVE_TICKS_STREAM_ERR = 19003

class TestIBClient(unittest.TestCase):
    """Unit tests for class `IBClient`."""
    _contract = ib_contract.Contract()
    _contract.secType = 'CASH'
    _contract.symbol = 'EUR'
    _contract.exchange = 'IDEALPRO'
    _contract.currency = 'GBP'

    @classmethod
    def setUpClass(cls):
        ibpy_client.IBClient.TZ = pytz.timezone('America/New_York')

        cls._wrapper = ibpy_wrapper.IBWrapper()
        cls._client = ibpy_client.IBClient(cls._wrapper)

        cls._client.connect(
            os.getenv('IB_HOST', '127.0.0.1'),
            int(os.getenv('IB_PORT', '4002')),
            1001
        )

        thread = threading.Thread(target=cls._client.run)
        thread.start()

        setattr(cls._client, "_thread", thread)

    @utils.async_test
    async def test_resolve_contract(self):
        """Test function `resolve_contract`."""
        contract = ib_contract.Contract()
        contract.secType = "FUT"
        contract.lastTradeDateOrContractMonth = "202006"
        contract.symbol = "MYM"
        contract.exchange = "ECBOT"
        contract.includeExpired = True

        resolved_contract = await self._client.resolve_contract(
            Const.RID_RESOLVE_CONTRACT.value, contract
        )

        self.assertIsNotNone(resolved_contract)
        print(resolved_contract)

    @utils.async_test
    async def test_resolve_head_timestamp(self):
        """Test function `resolve_head_timestamp`."""
        resolved_contract = await self._client.resolve_contract(
            Const.RID_RESOLVE_CONTRACT.value, self._contract
        )

        print(resolved_contract)

        head_timestamp = await self._client.resolve_head_timestamp(
            Const.RID_RESOLVE_HEAD_TIMESTAMP.value,
            resolved_contract,
            show='BID'
        )

        print(head_timestamp)

        self.assertIsNotNone(head_timestamp)
        self.assertIsInstance(head_timestamp, int)

    @utils.async_test
    async def test_fetch_historical_ticks(self):
        """Test function `fetch_historical_ticks`."""

        resolved_contract = await self._client.resolve_contract(
            Const.RID_RESOLVE_CONTRACT.value, self._contract
        )

        data = await self._client.fetch_historical_ticks(
            Const.RID_FETCH_HISTORICAL_TICKS.value, resolved_contract,
            start=ibpy_client.IBClient.TZ.localize(datetime\
                .datetime(2020, 4, 29, 10, 30, 0)),
            end=ibpy_client.IBClient.TZ.localize(datetime\
                .datetime(2020, 4, 29, 10, 31, 0)),
            show='MIDPOINT'
        )

        self.assertIsInstance(data[0], list)
        self.assertTrue(data[1], True)
        self.assertGreater(len(data[0]), 0)
        self.assertIsInstance(data[0][0], ib_wrapper.HistoricalTick)

        data = await self._client.fetch_historical_ticks(
            Const.RID_FETCH_HISTORICAL_TICKS.value, resolved_contract,
            start=ibpy_client.IBClient.TZ.localize(datetime\
                .datetime(2020, 4, 29, 10, 30, 0)),
            end=ibpy_client.IBClient.TZ.localize(datetime\
                .datetime(2020, 4, 29, 10, 31, 0)),
            show='BID_ASK'
        )

        self.assertIsInstance(data[0], list)
        self.assertTrue(data[1], True)
        self.assertGreater(len(data[0]), 0)
        self.assertIsInstance(data[0][0], ib_wrapper.HistoricalTickBidAsk)

    @utils.async_test
    async def test_fetch_historical_ticks_err(self):
        """Test function `fetch_historical_ticks` for the error cases."""
        resolved_contract = await self._client.resolve_contract(
            Const.RID_RESOLVE_CONTRACT.value, self._contract
        )

        # Incorrect value of `show`
        with self.assertRaises(ValueError):
            await self._client.fetch_historical_ticks(
                Const.RID_FETCH_HISTORICAL_TICKS_ERR.value, resolved_contract,
                datetime.datetime.now(), show='LAST'
            )

        # Timezone of start & end are not identical
        with self.assertRaises(ValueError):
            await self._client.fetch_historical_ticks(
                Const.RID_FETCH_HISTORICAL_TICKS_ERR.value, resolved_contract,
                datetime.datetime.now()\
                    .astimezone(pytz.timezone('Asia/Hong_Kong')),
                datetime.datetime.now()\
                    .astimezone(pytz.timezone('America/New_York'))
            )

        # Invalid contract object
        with self.assertRaises(error.IBError):
            await self._client.fetch_historical_ticks(
                Const.RID_FETCH_HISTORICAL_TICKS_ERR.value,
                ib_contract.Contract(),
                datetime.datetime(2020, 5, 20, 3, 20, 0)\
                    .astimezone(ibpy_client.IBClient.TZ),
                datetime.datetime.now().astimezone(ibpy_client.IBClient.TZ)
            )

    @utils.async_test
    async def test_stream_live_ticks(self):
        """Test function `stream_live_ticks`."""
        async def cancel_req():
            await asyncio.sleep(5)
            self._client.cancelTickByTickData(
                reqId=Const.RID_STREAM_LIVE_TICKS.value
            )

            queue = self._wrapper.get_request_queue_no_throw(
                req_id=Const.RID_STREAM_LIVE_TICKS
            )
            queue.put(fq.Status.FINISHED)

        resolved_contract = await self._client.resolve_contract(
            req_id=Const.RID_RESOLVE_CONTRACT.value, contract=self._contract
        )

        listener = _MockLiveTicksListener()

        stream = asyncio.create_task(
            self._client.stream_live_ticks(
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
        except error.IBError as err:
            tasks = asyncio.all_tasks()
            for task in tasks:
                task.cancel()

            raise err

        self.assertGreater(len(listener.ticks), 0)
        self.assertTrue(listener.finished)

    @utils.async_test
    async def test_cancel_live_ticks_stream(self):
        """Test function `cancel_live_ticks_stream`."""
        async def cancel_req():
            await asyncio.sleep(3)
            self._client.cancel_live_ticks_stream(
                req_id=Const.RID_CANCEL_LIVE_TICKS_STREAM.value
            )

        resolved_contract = await self._client.resolve_contract(
            req_id=Const.RID_RESOLVE_CONTRACT.value, contract=self._contract
        )

        listener = _MockLiveTicksListener()

        stream = asyncio.create_task(
            self._client.stream_live_ticks(
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
        except error.IBError as err:
            tasks = asyncio.all_tasks()
            for task in tasks:
                task.cancel()

            raise err

        self.assertTrue(listener.finished)

    @utils.async_test
    async def test_cancel_live_ticks_stream_err(self):
        """Test function `cancel_live_ticks_stream` with request ID that has no
        `FinishableQueue` associated with.
        """
        with self.assertRaises(error.IBError):
            self._client.cancel_live_ticks_stream(
                req_id=Const.RID_CANCEL_LIVE_TICKS_STREAM_ERR.value
            )

    @classmethod
    def tearDownClass(cls):
        cls._client.disconnect()
