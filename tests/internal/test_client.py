"""Unit tests for module `ibpy_native._internal._client`."""
# pylint: disable=protected-access
import asyncio
import datetime
import threading
import unittest

import pytz

from ibapi import contract
from ibapi import wrapper

from ibpy_native import error
from ibpy_native._internal import _client
from ibpy_native._internal import _global
from ibpy_native._internal import _wrapper
from ibpy_native.utils import datatype
from ibpy_native.utils import finishable_queue as fq

from tests.toolkit import sample_contracts
from tests.toolkit import utils

class TestContract(unittest.TestCase):
    """Unit tests for IB contract related functions in `IBClient`.

    Connection with IB is REQUIRED.
    """
    @classmethod
    def setUpClass(cls):
        cls._wrapper = _wrapper.IBWrapper()
        cls._client = _client.IBClient(cls._wrapper)

        cls._client.connect(utils.IB_HOST, utils.IB_PORT, utils.IB_CLIENT_ID)

        thread = threading.Thread(target=cls._client.run)
        thread.start()

    def setUp(self):
        self._req_id = self._wrapper.next_req_id

    @utils.async_test
    async def test_resolve_contracts(self):
        """Test function `resolve_contracts`."""
        result = await self._client.resolve_contracts(
            req_id=self._req_id, contract=sample_contracts.gbp_usd_fx())

        self.assertTrue(result)  # Expect item returned from request
        # Expect a propulated `ContractDetails` received from IB
        self.assertIsInstance(result[0], contract.ContractDetails)
        self.assertNotEqual(result[0].contract.conId, 0)

    @utils.async_test
    async def test_resolve_contracts_err_0(self):
        """Test function `resolve_contracts`.

        * Queue associated with `_req_id` is being occupied.
        """
        # Mock queue occupation
        self._wrapper.get_request_queue(req_id=self._req_id)
        with self.assertRaises(error.IBError): # Expect `IBError`
            await self._client.resolve_contracts(
                req_id=self._req_id, contract=sample_contracts.gbp_usd_fx())

    @utils.async_test
    async def test_resolve_contracts_err_1(self):
        """Test function `resolve_contracts`.

        * Error returned from IB for an non-resolvable `Contract`.
        """
        with self.assertRaises(error.IBError): # Expect `IBError`
            await self._client.resolve_contracts(
                req_id=self._req_id, contract=contract.Contract())

    @utils.async_test
    async def test_resolve_contracts_err_2(self):
        """Test function `resolve_contracts`.

        * No result received from IB.
        """
        invalid_contract = sample_contracts.us_future_expired()
        invalid_contract.includeExpired = False

        with self.assertRaises(error.IBError): # Expect `IBError`
            await self._client.resolve_contracts(
                req_id=self._req_id, contract=invalid_contract)

    @classmethod
    def tearDownClass(cls):
        cls._client.disconnect()

class TestHistoricalData(unittest.TestCase):
    """Unit tests for historical market data related function in `IBClient`.

    * Connection with IB is REQUIRED.
    * Subscription of US Futures market data is REQUIRED for some tests.
    """
    @classmethod
    def setUpClass(cls):
        cls._wrapper = _wrapper.IBWrapper()
        cls._client = _client.IBClient(cls._wrapper)

        cls._client.connect(utils.IB_HOST, utils.IB_PORT, utils.IB_CLIENT_ID)

        thread = threading.Thread(target=cls._client.run)
        thread.start()

    def setUp(self):
        self._req_id = self._wrapper.next_req_id
        self._start = (datetime.datetime.now().astimezone(_global.TZ) -
                       datetime.timedelta(minutes=5))
        self._end = datetime.datetime.now().astimezone(_global.TZ)

    @utils.async_test
    async def test_resolve_head_timestamp(self):
        """Test function `resolve_head_timestamp`."""
        result = await self._client.resolve_head_timestamp(
            req_id=self._req_id, contract=sample_contracts.gbp_usd_fx(),
            show=datatype.EarliestDataPoint.ASK
        )

        self.assertIsInstance(result, int) # Expect epoch returned as `int`
        self.assertGreater(result, 0) # Expect a valid epoch value

    @utils.async_test
    async def test_resolve_head_timestamp_err_0(self):
        """Test function `resolve_head_timestamp`.

        * Queue associated with `_req_id` is being occupied.
        """
        # Mock queue occupation
        self._wrapper.get_request_queue(req_id=self._req_id)
        with self.assertRaises(error.IBError):
            await self._client.resolve_head_timestamp(
                req_id=self._req_id, contract=sample_contracts.gbp_usd_fx(),
                show=datatype.EarliestDataPoint.ASK
            )

    @utils.async_test
    async def test_resolve_head_timestamp_err_1(self):
        """Test function `resolve_head_timestamp`.

        * Error returned from IB for non-resolvable `Contract`.
        """
        with self.assertRaises(error.IBError):
            await self._client.resolve_head_timestamp(
                req_id=self._req_id, contract=contract.Contract(),
                show=datatype.EarliestDataPoint.ASK
            )

    @utils.async_test
    async def test_fetch_historical_ticks_0(self):
        """Test function `fetch_historical_ticks`.

        * Request tick data for `BidAsk`.
        """
        result = await self._client.fetch_historical_ticks(
            req_id=self._req_id, contract=sample_contracts.gbp_usd_fx(),
            start=self._start, end=self._end,
            show=datatype.HistoricalTicks.BID_ASK
        )

        self.assertTrue(result)  # Expect data returned from IB
        self.assertIsInstance(result, dict)  # Expect data returned as `dict`
        # Expect ticks return in a list
        self.assertIsInstance(result["ticks"], list)
        # Expect `True` as a prove of all data within requested period are
        # received
        self.assertTrue(result["completed"])
        # Expect received tick type is `HistoricalTickBidAsk`
        self.assertIsInstance(result["ticks"][0], wrapper.HistoricalTickBidAsk)

    @utils.async_test
    async def test_fetch_historical_ticks_1(self):
        """Test function `fetch_historical_ticks`.

        * Request tick data for `MidPoint`.
        """
        result = await self._client.fetch_historical_ticks(
            req_id=self._req_id, contract=sample_contracts.gbp_usd_fx(),
            start=self._start, end=self._end,
            show=datatype.HistoricalTicks.MIDPOINT
        )

        self.assertTrue(result)  # Expect data returned from IB
        self.assertIsInstance(result, dict)  # Expect data returned as `dict`
        # Expect ticks return in a list
        self.assertIsInstance(result["ticks"], list)
        # Expect `True` as a prove of all data within requested period are
        # received
        self.assertTrue(result["completed"])
        # Expect received tick type is `HistoricalTickBidAsk`
        self.assertIsInstance(result["ticks"][0], wrapper.HistoricalTick)

    @utils.async_test
    async def test_fetch_historical_ticks_2(self):
        """Test function `fetch_historical_ticks`.

        * Request tick data for `Last`.
        """
        result = await self._client.fetch_historical_ticks(
            req_id=self._req_id, contract=sample_contracts.us_future(),
            start=self._start, end=self._end,
            show=datatype.HistoricalTicks.TRADES
        )

        self.assertTrue(result)  # Expect data returned from IB
        self.assertIsInstance(result, dict)  # Expect data returned as `dict`
        # Expect ticks return in a list
        self.assertIsInstance(result["ticks"], list)
        # Expect `True` as a prove of all data within requested period are
        # received
        self.assertTrue(result["completed"])
        # Expect received tick type is `HistoricalTickBidAsk`
        self.assertIsInstance(result["ticks"][0], wrapper.HistoricalTickLast)

    @utils.async_test
    async def test_fetch_historical_ticks_err_0(self):
        """Test function `fetch_historical_ticks`.

        * `ValueError` raised due to inconsistences timezone set for `start`
          and `end` time.
        """
        with self.assertRaises(ValueError):
            await self._client.fetch_historical_ticks(
                req_id=self._req_id, contract=sample_contracts.gbp_usd_fx(),
                start=datetime.datetime.now().astimezone(
                    pytz.timezone("Asia/Hong_Kong")
                ),
                end=self._end, show=datatype.HistoricalTicks.BID_ASK
            )

    @utils.async_test
    async def test_fetch_historical_ticks_err_1(self):
        """Test function `fetch_historical_ticks`.

        * `ValueError` raised due to value of `start` > `end`.
        """
        with self.assertRaises(ValueError):
            await self._client.fetch_historical_ticks(
                req_id=self._req_id, contract=sample_contracts.gbp_usd_fx(),
                start=self._end, end=self._start,
                show=datatype.HistoricalTicks.BID_ASK
            )

    @utils.async_test
    async def test_fetch_historical_ticks_err_2(self):
        """Test function `fetch_historical_ticks`.

        * `IBError` raised due to `req_id` is being occupied by other task.
        """
        # Mock queue occupation
        self._wrapper.get_request_queue(req_id=self._req_id)
        with self.assertRaises(error.IBError):
            await self._client.fetch_historical_ticks(
                req_id=self._req_id, contract=sample_contracts.gbp_usd_fx(),
                start=self._start, end=self._end,
                show=datatype.HistoricalTicks.BID_ASK
            )

    @utils.async_test
    async def test_fetch_historical_ticks_err_3(self):
        """Test function `fetch_historical_ticks`.

        * Error returned from IB for invalid contract.
        """
        with self.assertRaises(error.IBError):
            await self._client.fetch_historical_ticks(
                req_id=self._req_id, contract=contract.Contract(),
                start=self._start, end=self._end,
                show=datatype.HistoricalTicks.TRADES
            )

    @classmethod
    def tearDownClass(cls):
        cls._client.disconnect()

class TestLiveData(unittest.TestCase):
    """Unit tests for live market data related functions in `IBClient`.

    Connection with IB is REQUIRED.

    * Tests in this suit will hang up when the market is closed.
    """
    @classmethod
    def setUpClass(cls):
        cls._wrapper = _wrapper.IBWrapper()
        cls._client = _client.IBClient(cls._wrapper)

        cls._client.connect(utils.IB_HOST, utils.IB_PORT, utils.IB_CLIENT_ID)

        thread = threading.Thread(target=cls._client.run)
        thread.start()

    def setUp(self):
        self._req_id = self._wrapper.next_req_id
        self._listener = utils.MockLiveTicksListener()

    @utils.async_test
    async def test_stream_live_ticks(self):
        """Test function `stream_live_ticks`."""
        # Prepare function & tasks for the test
        async def cancel_req():
            while not self._listener.ticks: # Wait until a tick received
                await asyncio.sleep(0.1)
            await self._stop_streaming(req_id=self._req_id)

        cancel_task = asyncio.create_task(cancel_req())

        try:
            await self._start_streaming(req_id=self._req_id)
            await cancel_task
        except error.IBError as err:
            for task in asyncio.all_tasks():
                task.cancel()
            self.fail(err.err_str)

        self.assertIsInstance(self._listener.ticks[0],
                              wrapper.HistoricalTickBidAsk)

    @utils.async_test
    async def test_stream_live_ticks_err(self):
        """Test function `stream_live_ticks`.

        * Should raise `IBError` as queue associated with `_req_id` being
          occupied.
        """
        # Mock queue occupation
        self._wrapper.get_request_queue(req_id=self._req_id)
        with self.assertRaises(error.IBError):
            await self._client.stream_live_ticks(
                req_id=self._req_id, contract=sample_contracts.gbp_usd_fx(),
                listener=self._listener, tick_type=datatype.LiveTicks.BID_ASK
            )

    @utils.async_test
    async def test_cancel_live_ticks_stream(self):
        """Test function `cancel_live_ticks_stream`."""
        try:
            await self._start_streaming(req_id=self._req_id)
            await asyncio.sleep(0.5)
            self._client.cancel_live_ticks_stream(req_id=self._req_id)
        except error.IBError as err:
            for task in asyncio.all_tasks():
                task.cancel()
            self.fail(err.err_str)

        await asyncio.sleep(0.5)
        self.assertTrue(self._listener.finished)

    @utils.async_test
    async def test_cancel_live_ticks_stream_err(self):
        """Test function `cancel_live_ticks_stream`.

        * Should raise `IBError` as no queue is associated with `_req_id`.
        """
        with self.assertRaises(error.IBError):
            self._client.cancel_live_ticks_stream(req_id=self._req_id)

    @classmethod
    def tearDownClass(cls):
        cls._client.disconnect()

    async def _start_streaming(self, req_id: int) -> asyncio.Task:
        return asyncio.create_task(self._client.stream_live_ticks(
                req_id, contract=sample_contracts.gbp_usd_fx(),
                listener=self._listener, tick_type=datatype.LiveTicks.BID_ASK
            )
        )

    async def _stop_streaming(self, req_id: int):
        self._client.cancelTickByTickData(reqId=req_id)
        await asyncio.sleep(2)
        self._wrapper.get_request_queue_no_throw(req_id).put(fq.Status.FINISHED)
