"""Unit tests for module `ibpy_native.bridge`."""
# pylint: disable=protected-access
import asyncio
import datetime
import os
import unittest

import pytz

from ibapi import contract as ib_contract

import ibpy_native
from ibpy_native import error
from ibpy_native.interfaces import listeners
from ibpy_native.internal import client as ibpy_client
from ibpy_native.utils import datatype as dt

from tests.toolkit import sample_contracts
from tests.toolkit import utils

TEST_HOST = os.getenv('IB_HOST', '127.0.0.1')
TEST_PORT = int(os.getenv('IB_PORT', '4002'))
TEST_ID = 1001

class TestIBBridgeConn(unittest.TestCase):
    """Test cases for connection related functions in `IBBridge`."""

    def test_init_auto_connect(self):
        """Test initialise `IBBridge` with `auto_conn=True`."""
        bridge = ibpy_native.IBBridge(
            host=TEST_HOST, port=TEST_PORT, client_id=TEST_ID
        )

        self.assertTrue(bridge.is_connected())

        bridge.disconnect()

    def test_init_manual_connect(self):
        """Test initialise `IBBridge` with `auto_conn=False`."""
        bridge = ibpy_native.IBBridge(
            host=TEST_HOST, port=TEST_PORT, client_id=TEST_ID, auto_conn=False
        )
        bridge.connect()

        self.assertTrue(bridge.is_connected())

        bridge.disconnect()

    def test_disconnect_without_connection(self):
        """Test function `disconnect` without an established connection."""
        bridge = ibpy_native.IBBridge(
            host=TEST_HOST, port=TEST_PORT, client_id=TEST_ID, auto_conn=False
        )
        bridge.disconnect()

        self.assertFalse(bridge.is_connected())

class TestIBBridge(unittest.TestCase):
    """Unit tests for class `IBBridge`."""

    @classmethod
    def setUpClass(cls):
        cls._bridge = ibpy_native.IBBridge(
            host=TEST_HOST, port=TEST_PORT, client_id=TEST_ID
        )

    def test_set_timezone(self):
        """Test function `set_timezone`."""
        ibpy_native.IBBridge.set_timezone(tz=pytz.timezone('Asia/Hong_Kong'))

        self.assertEqual(ibpy_client._IBClient.TZ,
                         pytz.timezone('Asia/Hong_Kong'))

        # Reset timezone to New York
        ibpy_native.IBBridge.set_timezone(tz=pytz.timezone('America/New_York'))
        self.assertEqual(ibpy_client._IBClient.TZ,
                         pytz.timezone('America/New_York'))

    def test_set_on_notify_listener(self):
        """Test notification listener supports."""
        class MockListener(listeners.NotificationListener):
            """Mock notification listener"""
            triggered = False

            def on_notify(self, msg_code: int, msg: str):
                """Mock callback implementation"""
                print(f"{msg_code} - {msg}")

                self.triggered = True

        mock_listener = MockListener()

        self._bridge.set_on_notify_listener(listener=mock_listener)
        self._bridge._wrapper.error(
            reqId=-1, errorCode=1100, errorString="MOCK MSG"
        )

    @utils.async_test
    async def test_get_us_stock_contract(self):
        """Test function `get_us_stock_contract`."""
        contract = await self._bridge.get_us_stock_contract(symbol='AAPL')

        self.assertIsInstance(contract, ib_contract.Contract)

    @utils.async_test
    async def test_get_us_future_contract(self):
        """Test function `get_us_future_contract`."""
        contract = await self._bridge.get_us_future_contract(symbol='MYM')
        self.assertIsInstance(contract, ib_contract.Contract)

        with self.assertRaises(ValueError):
            await self._bridge.get_us_future_contract(symbol='MYM',
                                                      contract_month='abcd')

    @utils.async_test
    async def test_get_earliest_data_point(self):
        """Test function `get_earliest_data_point`."""
        head_trade = await self._bridge.get_earliest_data_point(
            contract=sample_contracts.us_stock()
        )
        self.assertEqual(datetime.datetime(1980, 12, 12, 9, 30), head_trade)

        head_bid = await self._bridge.get_earliest_data_point(
            contract=sample_contracts.us_stock(),
            data_type=dt.EarliestDataPoint.BID
        )
        self.assertEqual(datetime.datetime(2008, 12, 29, 7, 0), head_bid)

    @utils.async_test
    async def test_get_historical_ticks(self):
        """Test function `get_historical_ticks`."""
        result = await self._bridge.get_historical_ticks(
            contract=sample_contracts.us_stock(),
            start=datetime.datetime(2020, 3, 16, 9, 30),
            end=datetime.datetime(2020, 3, 16, 9, 50)
        )

        self.assertTrue(result['ticks'])
        self.assertTrue(result['completed'])

    @utils.async_test
    async def test_get_historical_ticks_err(self):
        """Test function `get_historical_ticks` for the error cases."""
        # start/end should not contains timezone info
        with self.assertRaises(ValueError):
            await self._bridge.get_historical_ticks(
                contract=sample_contracts.us_stock(),
                end=pytz.timezone('Asia/Hong_Kong').localize(
                    datetime.datetime(2020, 4, 28)
                )
            )

        # `start` is earlier than earliest available data point
        with self.assertRaises(ValueError):
            await self._bridge.get_historical_ticks(
                contract=sample_contracts.us_stock(),
                start=datetime.datetime(1972, 12, 12)
            )

        # `end` is earlier than `start`
        with self.assertRaises(ValueError):
            await self._bridge.get_historical_ticks(
                contract=sample_contracts.us_stock(),
                start=datetime.datetime(2020, 4, 29, 9, 30),
                end=datetime.datetime(2020, 4, 28, 9, 30)
            )

        # Invalid `attempts` value
        with self.assertRaises(ValueError):
            await self._bridge.get_historical_ticks(
                contract=sample_contracts.us_stock(), attempts=0
            )

    @utils.async_test
    async def test_stream_live_ticks(self):
        """Test function `stream_live_ticks`."""
        client: ibpy_client._IBClient = self._bridge._client
        listener = utils.MockLiveTicksListener()

        req_id = await self._bridge.stream_live_ticks(
            contract=sample_contracts.gbp_usd_fx(),
            listener=listener, tick_type=dt.LiveTicks.BID_ASK
        )
        self.assertIsNotNone(req_id)

        await asyncio.sleep(5)
        self.assertTrue(listener.ticks)
        client.cancel_live_ticks_stream(req_id=req_id)
        await asyncio.sleep(0.5)

    @utils.async_test
    async def test_stop_live_ticks_stream(self):
        """Test functions `stop_live_ticks_stream`."""
        listener = utils.MockLiveTicksListener()

        stream_id = await self._bridge.stream_live_ticks(
            contract=sample_contracts.gbp_usd_fx(),
            listener=listener, tick_type=dt.LiveTicks.BID_ASK
        )

        await asyncio.sleep(2)
        self._bridge.stop_live_ticks_stream(stream_id=stream_id)
        await asyncio.sleep(0.5)
        self.assertTrue(listener.finished)

    def test_stop_live_ticks_stream_err(self):
        """Test functions `stop_live_ticks_stream` for the error cases."""
        with self.assertRaises(error.IBError):
            self._bridge.stop_live_ticks_stream(stream_id=9999999)

    @classmethod
    def tearDownClass(cls):
        cls._bridge.disconnect()
