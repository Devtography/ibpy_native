"""Unit tests for module `ibpy_native.bridge`."""
import asyncio
import datetime
import os
import unittest
from typing import List, Union

import pytz

from ibapi import contract as ib_contract
from ibapi import wrapper as ib_wrapper

import ibpy_native
from ibpy_native import error
from ibpy_native.interfaces import listeners
from ibpy_native.internal import client as ibpy_client
from ibpy_native.utils import datatype as dt

from tests import utils

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
        ibpy_native.IBBridge.set_timezone(pytz.timezone('Asia/Hong_Kong'))

        self.assertEqual(ibpy_client.IBClient.TZ,
                         pytz.timezone('Asia/Hong_Kong'))

        # Reset timezone to New York
        ibpy_native.IBBridge.set_timezone(pytz.timezone('America/New_York'))
        self.assertEqual(ibpy_client.IBClient.TZ,
                         pytz.timezone('America/New_York'))

    def test_set_on_notify_listener(self):
        """Test notification listener supports."""
        # pylint: disable=protected-access
        class MockListener(listeners.NotificationListener):
            """Mock notification listener"""
            triggered = False

            def on_notify(self, msg_code: int, msg: str):
                """Mock callback implementation"""
                print(f"{msg_code} - {msg}")

                self.triggered = True

        mock_listener = MockListener()

        self._bridge.set_on_notify_listener(mock_listener)
        self._bridge._IBBridge__wrapper.error(
            reqId=-1, errorCode=1100, errorString="MOCK MSG"
        )

    @utils.async_test
    async def test_get_us_stock_contract(self):
        """Test function `get_us_stock_contract`."""
        contract = await self._bridge.get_us_stock_contract('AAPL')

        self.assertIsInstance(contract, ib_contract.Contract)

    @utils.async_test
    async def test_get_us_future_contract(self):
        """Test function `get_us_future_contract`."""
        contract = await self._bridge.get_us_future_contract('MYM')
        self.assertIsInstance(contract, ib_contract.Contract)

        with self.assertRaises(ValueError):
            await self._bridge.get_us_future_contract('MYM', 'abcd')

    @utils.async_test
    async def test_get_earliest_data_point(self):
        """Test function `get_earliest_data_point`."""
        contract = await self._bridge.get_us_stock_contract('AAPL')

        head_trade = await self._bridge.get_earliest_data_point(contract)
        self.assertEqual(datetime.datetime(1980, 12, 12, 9, 30), head_trade)

        head_bid_ask = await self._bridge.get_earliest_data_point(
            contract, 'BID_ASK'
        )
        self.assertEqual(datetime.datetime(2004, 1, 23, 9, 30), head_bid_ask)

    @utils.async_test
    async def test_get_historical_ticks(self):
        """Test function `get_historical_ticks`."""
        contract = await self._bridge.get_us_future_contract('mym', '202003')

        result = await self._bridge.get_historical_ticks(
            contract,
            datetime.datetime(2020, 3, 16, 6, 30),
            datetime.datetime(2020, 3, 16, 11, 0, 0)
        )

        self.assertGreater(len(result['ticks']), 0)
        self.assertTrue(result['completed'])

    @utils.async_test
    async def test_get_historical_ticks_err(self):
        """Test function `get_historical_ticks` for the error cases."""
        contract = await self._bridge.get_us_stock_contract('AAPL')

        # start/end should not contains timezone info
        with self.assertRaises(ValueError):
            await self._bridge.get_historical_ticks(
                contract, end=pytz.timezone('Asia/Hong_Kong').localize(
                    datetime.datetime(2020, 4, 28)
                )
            )

        # Invalid `data_type`
        with self.assertRaises(ValueError):
            await self._bridge.get_historical_ticks(
                contract,
                data_type='BID'
            )

        # `start` is earlier than earliest available data point
        with self.assertRaises(ValueError):
            await self._bridge.get_historical_ticks(
                contract, datetime.datetime(1972, 12, 12)
            )

        # `end` is earlier than `start`
        with self.assertRaises(ValueError):
            await self._bridge.get_historical_ticks(
                contract,
                start=datetime.datetime(2020, 4, 29, 9, 30),
                end=datetime.datetime(2020, 4, 28, 9, 30)
            )

        # Invalid `attempts` value
        with self.assertRaises(ValueError):
            await self._bridge.get_historical_ticks(
                contract, attempts=0
            )

    @utils.async_test
    async def test_stream_live_ticks(self):
        """Test function `stream_live_ticks`."""
        # pylint: disable=protected-access
        class MockListener(listeners.LiveTicksListener):
            """Mock notification listener"""
            ticks: List[Union[ib_wrapper.HistoricalTick,
                              ib_wrapper.HistoricalTickBidAsk,
                              ib_wrapper.HistoricalTickLast]] = []

            def on_tick_receive(self, req_id: int,
                                tick: Union[ib_wrapper.HistoricalTick,
                                            ib_wrapper.HistoricalTickBidAsk,
                                            ib_wrapper.HistoricalTickLast]):
                print(tick)
                self.ticks.append(tick)

            def on_finish(self, req_id: int):
                pass

            def on_err(self, err: error.IBError):
                raise err

        client: ibpy_client.IBClient = self._bridge._IBBridge__client
        listener = MockListener()

        contract = ib_contract.Contract()
        contract.secType = 'CASH'
        contract.symbol = 'EUR'
        contract.exchange = 'IDEALPRO'
        contract.currency = 'GBP'

        resolved = await client.resolve_contract(
            req_id=1, contract=contract
        )

        req_id = await self._bridge.stream_live_ticks(
            contract=resolved, listener=listener, tick_type=dt.LiveTicks.BID_ASK
        )
        self.assertIsNotNone(req_id)

        await asyncio.sleep(5)
        self.assertTrue(listener.ticks)
        client.cancel_live_ticks_stream(req_id=req_id)
        await asyncio.sleep(0.5)

    @utils.async_test
    async def test_stop_live_ticks_stream(self):
        """Test functions `stop_live_ticks_stream`."""
        # pylint: disable=protected-access
        class MockListener(listeners.LiveTicksListener):
            """Mock notification listener"""
            finished: bool = False

            def on_tick_receive(self, req_id: int,
                                tick: Union[ib_wrapper.HistoricalTick,
                                            ib_wrapper.HistoricalTickBidAsk,
                                            ib_wrapper.HistoricalTickLast]):
                print(tick)

            def on_finish(self, req_id: int):
                self.finished = True

            def on_err(self, err: error.IBError):
                raise err

        client: ibpy_client.IBClient = self._bridge._IBBridge__client
        listener = MockListener()

        contract = ib_contract.Contract()
        contract.secType = 'CASH'
        contract.symbol = 'EUR'
        contract.exchange = 'IDEALPRO'
        contract.currency = 'GBP'

        resolved = await client.resolve_contract(
            req_id=1, contract=contract
        )

        stream_id = await self._bridge.stream_live_ticks(
            contract=resolved, listener=listener, tick_type=dt.LiveTicks.BID_ASK
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
