"""Unit tests for module `ibpy_native.client`."""
# pylint: disable=protected-access
import asyncio
import datetime
import threading
import unittest
from typing import List

import pytz

from ibapi import contract as ib_contract
from ibapi import wrapper as ib_wrapper

from ibpy_native import error
from ibpy_native._internal import _client
from ibpy_native._internal import _global
from ibpy_native._internal import _wrapper
from ibpy_native.utils import datatype as dt
from ibpy_native.utils import finishable_queue as fq

from tests.toolkit import sample_contracts
from tests.toolkit import utils

#region - Constants
# Predefined request IDs for tests in `TestIBClient`.
_RID_RESOLVE_CONTRACT = 43
_RID_RESOLVE_CONTRACTS = 44
_RID_RESOLVE_HEAD_TIMESTAMP = 14001
_RID_RESOLVE_HEAD_TIMESTAMP_EPOCH = 14002
_RID_FETCH_HISTORICAL_TICKS = 18001
_RID_FETCH_HISTORICAL_TICKS_ERR = 18002
_RID_STREAM_LIVE_TICKS = 19001
_RID_CANCEL_LIVE_TICKS_STREAM = 19002
_RID_CANCEL_LIVE_TICKS_STREAM_ERR = 19003
#endregion - Constants

class TestIBClient(unittest.TestCase):
    """Unit tests for class `IBClient`."""

    @classmethod
    def setUpClass(cls):
        _global.TZ = pytz.timezone("America/New_York")

        cls._wrapper = _wrapper.IBWrapper()
        cls._client = _client.IBClient(cls._wrapper)

        cls._client.connect(utils.IB_HOST, utils.IB_PORT, utils.IB_CLIENT_ID)

        thread = threading.Thread(target=cls._client.run)
        thread.start()

        setattr(cls._client, "_thread", thread)

    #region - Contract
    @utils.async_test
    async def test_resolve_contract(self):
        """Test function `resolve_contract`."""
        resolved_contract = await self._client.resolve_contract(
            req_id=_RID_RESOLVE_CONTRACT,
            contract=sample_contracts.gbp_usd_fx()
        )

        self.assertIsNotNone(resolved_contract)

    @utils.async_test
    async def test_resolve_contracts(self):
        """Test function `resolve_contracts`."""
        contract: ib_contract.Contract = sample_contracts.us_future()
        contract.lastTradeDateOrContractMonth = ""

        res: List[ib_contract.ContractDetails] = (
            await self._client.resolve_contracts(req_id=_RID_RESOLVE_CONTRACTS,
                                                 contract=contract)
        )

        self.assertTrue(res)
        self.assertGreater(len(res), 1)
    #endregion - Contract

    @utils.async_test
    async def test_resolve_head_timestamp(self):
        """Test function `resolve_head_timestamp`."""
        head_timestamp = await self._client.resolve_head_timestamp(
            req_id=_RID_RESOLVE_HEAD_TIMESTAMP,
            contract=sample_contracts.gbp_usd_fx(),
            show=dt.EarliestDataPoint.BID
        )

        self.assertIsNotNone(head_timestamp)
        self.assertIsInstance(head_timestamp, int)

    #region - Historical ticks
    @utils.async_test
    async def test_fetch_historical_ticks(self):
        """Test function `fetch_historical_ticks`."""
        data = await self._client.fetch_historical_ticks(
            req_id=_RID_FETCH_HISTORICAL_TICKS,
            contract=sample_contracts.us_stock(),
            start=_global.TZ.localize(
                datetime.datetime(2020, 4, 29, 10, 30, 0)),
            end=_global.TZ.localize(
                datetime.datetime(2020, 4, 29, 10, 35, 0)),
            show=dt.HistoricalTicks.MIDPOINT
        )

        self.assertIsInstance(data["ticks"], list)
        self.assertTrue(data["completed"])
        self.assertTrue(data["ticks"])
        self.assertIsInstance(data["ticks"][0], ib_wrapper.HistoricalTick)

        data = await self._client.fetch_historical_ticks(
            req_id=_RID_FETCH_HISTORICAL_TICKS,
            contract=sample_contracts.us_stock(),
            start=_global.TZ.localize(
                datetime.datetime(2020, 4, 29, 10, 30, 0)),
            end=_global.TZ.localize(
                datetime.datetime(2020, 4, 29, 10, 35, 0)),
            show=dt.HistoricalTicks.BID_ASK
        )

        self.assertIsInstance(data["ticks"], list)
        self.assertTrue(data["completed"])
        self.assertTrue(data["ticks"])
        self.assertIsInstance(data["ticks"][0], ib_wrapper.HistoricalTickBidAsk)

    @utils.async_test
    async def test_fetch_historical_ticks_err(self):
        """Test function `fetch_historical_ticks` for the error cases."""
        # Timezone of start & end are not identical
        with self.assertRaises(ValueError):
            await self._client.fetch_historical_ticks(
                req_id=_RID_FETCH_HISTORICAL_TICKS_ERR,
                contract=sample_contracts.gbp_usd_fx(),
                start=datetime.datetime.now().astimezone(
                    pytz.timezone("Asia/Hong_Kong")),
                end=datetime.datetime.now().astimezone(
                    pytz.timezone("America/New_York"))
            )

        # Invalid contract object
        with self.assertRaises(error.IBError):
            await self._client.fetch_historical_ticks(
                req_id=_RID_FETCH_HISTORICAL_TICKS_ERR,
                contract=ib_contract.Contract(),
                start=datetime.datetime(2020, 5, 20, 3, 20, 0).astimezone(
                    _global.TZ),
                end=datetime.datetime.now().astimezone(_global.TZ)
            )
    #endregion - Historical ticks

    #region - Live ticks
    @utils.async_test
    async def test_stream_live_ticks(self):
        """Test function `stream_live_ticks`."""
        async def cancel_req():
            await asyncio.sleep(5)
            self._client.cancelTickByTickData(
                reqId=_RID_STREAM_LIVE_TICKS
            )

            queue = self._wrapper.get_request_queue_no_throw(
                req_id=_RID_STREAM_LIVE_TICKS
            )
            queue.put(element=fq.Status.FINISHED)

        listener = utils.MockLiveTicksListener()

        stream = asyncio.create_task(
            self._client.stream_live_ticks(
                req_id=_RID_STREAM_LIVE_TICKS,
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
                req_id=_RID_CANCEL_LIVE_TICKS_STREAM
            )

        listener = utils.MockLiveTicksListener()

        stream = asyncio.create_task(
            self._client.stream_live_ticks(
                req_id=_RID_CANCEL_LIVE_TICKS_STREAM,
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
        `FinishableQueue` associated with.
        """
        with self.assertRaises(error.IBError):
            self._client.cancel_live_ticks_stream(
                req_id=_RID_CANCEL_LIVE_TICKS_STREAM_ERR
            )
    #endregion - Live ticks

    @classmethod
    def tearDownClass(cls):
        cls._client.disconnect()
