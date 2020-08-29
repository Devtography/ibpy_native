"""Unit tests for module `ibpy_native.client`."""
# pylint: disable=protected-access
import asyncio
import datetime
import enum
import os
import threading
import unittest
from typing import List

import pytz

from ibapi import contract as ib_contract
from ibapi import wrapper as ib_wrapper

from ibpy_native import error
from ibpy_native.internal import client as ibpy_client
from ibpy_native.internal import wrapper as ibpy_wrapper
from ibpy_native.utils import datatype as dt
from ibpy_native.utils import finishable_queue as fq

from tests.toolkit import sample_contracts
from tests.toolkit import utils

class Const(enum.IntEnum):
    """Predefined request IDs for tests in `TestIBClient`."""
    RID_RESOLVE_CONTRACT = 43
    RID_RESOLVE_CONTRACTS = 44
    RID_RESOLVE_HEAD_TIMESTAMP = 14001
    RID_RESOLVE_HEAD_TIMESTAMP_EPOCH = 14002
    RID_FETCH_HISTORICAL_TICKS = 18001
    RID_FETCH_HISTORICAL_TICKS_ERR = 18002
    RID_STREAM_LIVE_TICKS = 19001
    RID_CANCEL_LIVE_TICKS_STREAM = 19002
    RID_CANCEL_LIVE_TICKS_STREAM_ERR = 19003

class TestIBClient(unittest.TestCase):
    """Unit tests for class `_IBClient`."""

    @classmethod
    def setUpClass(cls):
        ibpy_client._IBClient.TZ = pytz.timezone('America/New_York')

        cls._wrapper = ibpy_wrapper._IBWrapper()
        cls._client = ibpy_client._IBClient(cls._wrapper)

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
        resolved_contract = await self._client.resolve_contract(
            req_id=Const.RID_RESOLVE_CONTRACT.value,
            contract=sample_contracts.gbp_usd_fx()
        )

        self.assertIsNotNone(resolved_contract)
        print(resolved_contract)

    @utils.async_test
    async def test_resolve_contracts(self):
        """Test function `resolve_contracts`."""
        contract: ib_contract.Contract = sample_contracts.us_future()
        contract.lastTradeDateOrContractMonth = ''

        res: List[ib_contract.ContractDetails] = await self._client\
            .resolve_contracts(req_id=Const.RID_RESOLVE_CONTRACTS.value,
                               contract=contract)

        self.assertTrue(res)
        self.assertGreater(len(res), 1)

    @utils.async_test
    async def test_resolve_head_timestamp(self):
        """Test function `resolve_head_timestamp`."""
        head_timestamp = await self._client.resolve_head_timestamp(
            req_id=Const.RID_RESOLVE_HEAD_TIMESTAMP.value,
            contract=sample_contracts.us_future(),
            show=dt.EarliestDataPoint.BID
        )

        print(head_timestamp)

        self.assertIsNotNone(head_timestamp)
        self.assertIsInstance(head_timestamp, int)

    @utils.async_test
    async def test_fetch_historical_ticks(self):
        """Test function `fetch_historical_ticks`."""
        data = await self._client.fetch_historical_ticks(
            req_id=Const.RID_FETCH_HISTORICAL_TICKS.value,
            contract=sample_contracts.gbp_usd_fx(),
            start=ibpy_client._IBClient.TZ.localize(datetime\
                .datetime(2020, 4, 29, 10, 30, 0)),
            end=ibpy_client._IBClient.TZ.localize(datetime\
                .datetime(2020, 4, 29, 10, 35, 0)),
            show=dt.HistoricalTicks.MIDPOINT
        )

        self.assertIsInstance(data['ticks'], list)
        self.assertTrue(data['completed'])
        self.assertTrue(data['ticks'])
        self.assertIsInstance(data['ticks'][0], ib_wrapper.HistoricalTick)

        data = await self._client.fetch_historical_ticks(
            req_id=Const.RID_FETCH_HISTORICAL_TICKS.value,
            contract=sample_contracts.gbp_usd_fx(),
            start=ibpy_client._IBClient.TZ.localize(datetime\
                .datetime(2020, 4, 29, 10, 30, 0)),
            end=ibpy_client._IBClient.TZ.localize(datetime\
                .datetime(2020, 4, 29, 10, 35, 0)),
            show=dt.HistoricalTicks.BID_ASK
        )

        self.assertIsInstance(data['ticks'], list)
        self.assertTrue(data['completed'])
        self.assertTrue(data['ticks'])
        self.assertIsInstance(data['ticks'][0], ib_wrapper.HistoricalTickBidAsk)

    @utils.async_test
    async def test_fetch_historical_ticks_err(self):
        """Test function `fetch_historical_ticks` for the error cases."""
        # Timezone of start & end are not identical
        with self.assertRaises(ValueError):
            await self._client.fetch_historical_ticks(
                req_id=Const.RID_FETCH_HISTORICAL_TICKS_ERR.value,
                contract=sample_contracts.gbp_usd_fx(),
                start=datetime.datetime.now()\
                    .astimezone(pytz.timezone('Asia/Hong_Kong')),
                end=datetime.datetime.now()\
                    .astimezone(pytz.timezone('America/New_York'))
            )

        # Invalid contract object
        with self.assertRaises(error.IBError):
            await self._client.fetch_historical_ticks(
                req_id=Const.RID_FETCH_HISTORICAL_TICKS_ERR.value,
                contract=ib_contract.Contract(),
                start=datetime.datetime(2020, 5, 20, 3, 20, 0)\
                    .astimezone(ibpy_client._IBClient.TZ),
                end=datetime.datetime.now().astimezone(ibpy_client._IBClient.TZ)
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
            queue.put(element=fq._Status.FINISHED)

        listener = utils.MockLiveTicksListener()

        stream = asyncio.create_task(
            self._client.stream_live_ticks(
                req_id=Const.RID_STREAM_LIVE_TICKS.value,
                contract=sample_contracts.gbp_usd_fx(),
                listener=listener,
                tick_type=dt.LiveTicks.BID_ASK
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

        self.assertTrue(listener.ticks)
        self.assertTrue(listener.finished)

    @utils.async_test
    async def test_cancel_live_ticks_stream(self):
        """Test function `cancel_live_ticks_stream`."""
        async def cancel_req():
            await asyncio.sleep(3)
            self._client.cancel_live_ticks_stream(
                req_id=Const.RID_CANCEL_LIVE_TICKS_STREAM.value
            )

        listener = utils.MockLiveTicksListener()

        stream = asyncio.create_task(
            self._client.stream_live_ticks(
                req_id=Const.RID_CANCEL_LIVE_TICKS_STREAM.value,
                contract=sample_contracts.gbp_usd_fx(),
                listener=listener,
                tick_type=dt.LiveTicks.BID_ASK
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
        `_FinishableQueue` associated with.
        """
        with self.assertRaises(error.IBError):
            self._client.cancel_live_ticks_stream(
                req_id=Const.RID_CANCEL_LIVE_TICKS_STREAM_ERR.value
            )

    @classmethod
    def tearDownClass(cls):
        cls._client.disconnect()
