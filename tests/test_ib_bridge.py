"""Unit tests for module `ibpy_native.bridge`."""
# pylint: disable=protected-access
import asyncio
import datetime
import os
import unittest

import pytz

import ibpy_native
from ibpy_native import error
from ibpy_native._internal import _client
from ibpy_native._internal import _global
from ibpy_native.interfaces import listeners
from ibpy_native.utils import datatype as dt, finishable_queue as fq

from tests.toolkit import sample_contracts
from tests.toolkit import utils

class TestIBBridgeConn(unittest.TestCase):
    """Test cases for connection related functions in `IBBridge`."""

    def test_init_auto_connect(self):
        """Test initialise `IBBridge` with `auto_conn=True`."""
        bridge = ibpy_native.IBBridge(host=utils.IB_HOST, port=utils.IB_PORT,
                                      client_id=utils.IB_CLIENT_ID)

        self.assertTrue(bridge.is_connected())

        bridge.disconnect()

    def test_init_manual_connect(self):
        """Test initialise `IBBridge` with `auto_conn=False`."""
        bridge = ibpy_native.IBBridge(host=utils.IB_HOST,
                                      port=utils.IB_PORT,
                                      client_id=utils.IB_CLIENT_ID,
                                      auto_conn=False)
        bridge.connect()

        self.assertTrue(bridge.is_connected())

        bridge.disconnect()

    def test_disconnect_without_connection(self):
        """Test function `disconnect` without an established connection."""
        bridge = ibpy_native.IBBridge(host=utils.IB_HOST,
                                      port=utils.IB_PORT,
                                      client_id=utils.IB_CLIENT_ID,
                                      auto_conn=False)
        bridge.disconnect()

        self.assertFalse(bridge.is_connected())

class TestIBBridge(unittest.TestCase):
    """Unit tests for class `IBBridge`."""

    @classmethod
    def setUpClass(cls):
        cls._bridge = ibpy_native.IBBridge(
            host=utils.IB_HOST, port=utils.IB_PORT, client_id=utils.IB_CLIENT_ID
        )

    @utils.async_test
    async def test_accounts_manager(self):
        """Test if the `AccountsManager` is properly set up and has the
        account(s) received from IB Gateway once logged in.
        """
        await asyncio.sleep(0.5) # Wait for the Gateway to return account ID(s).
        self.assertTrue(self._bridge.accounts_manager.accounts)

    def test_set_timezone(self):
        """Test function `set_timezone`."""
        ibpy_native.IBBridge.set_timezone(tz=pytz.timezone("Asia/Hong_Kong"))

        self.assertEqual(_global.TZ,
                         pytz.timezone("Asia/Hong_Kong"))

        # Reset timezone to New York
        ibpy_native.IBBridge.set_timezone(tz=pytz.timezone("America/New_York"))
        self.assertEqual(_global.TZ,
                         pytz.timezone("America/New_York"))

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

    #region - IB account related
    @utils.async_test
    async def test_req_managed_accounts(self):
        """Test function `req_managed_accounts`."""
        await asyncio.sleep(0.5)
        # Clean up the already filled dict.
        self._bridge.accounts_manager.accounts.clear()

        self._bridge.req_managed_accounts()

        await asyncio.sleep(0.5)
        self.assertTrue(self._bridge.accounts_manager.accounts)

    @utils.async_test
    async def test_account_updates(self):
        """Test functions `sub_acccount_updates` & `unsub_account_updates`."""
        await asyncio.sleep(0.5)
        account = self._bridge.accounts_manager.accounts[os.getenv("IB_ACC_ID")]

        await self._bridge.sub_account_updates(account=account)
        await asyncio.sleep(0.5)
        await self._bridge.unsub_account_updates(account=account)
        await asyncio.sleep(0.5)

        self.assertTrue(account.account_ready)
        self.assertEqual(
            self._bridge.accounts_manager.account_updates_queue.status,
            fq.Status.FINISHED
        )
    #endregion - IB account related

    @utils.async_test
    async def test_search_detailed_contracts(self):
        """Test function `search_detailed_contracts`."""
        contract = sample_contracts.us_future()
        contract.lastTradeDateOrContractMonth = ""

        res = await self._bridge.search_detailed_contracts(contract=contract)
        self.assertGreater(len(res), 1)
        for item in res:
            print(item.contract)

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

    #region - Historical ticks
    @utils.async_test
    async def test_get_historical_ticks(self):
        """Test function `get_historical_ticks`."""
        result = await self._bridge.get_historical_ticks(
            contract=sample_contracts.us_stock(),
            start=datetime.datetime(2020, 3, 16, 9, 30),
            end=datetime.datetime(2020, 3, 16, 9, 50)
        )

        self.assertTrue(result["ticks"])
        self.assertTrue(result["completed"])

    @utils.async_test
    async def test_get_historical_ticks_err(self):
        """Test function `get_historical_ticks` for the error cases."""
        # start/end should not contains timezone info
        with self.assertRaises(ValueError):
            await self._bridge.get_historical_ticks(
                contract=sample_contracts.us_stock(),
                end=pytz.timezone("Asia/Hong_Kong").localize(
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
    #endregion - Historical ticks

    #region - Live ticks
    @utils.async_test
    async def test_stream_live_ticks(self):
        """Test function `stream_live_ticks`."""
        client: _client.IBClient = self._bridge._client
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
    #endregion - Live ticks

    @classmethod
    def tearDownClass(cls):
        cls._bridge.disconnect()
