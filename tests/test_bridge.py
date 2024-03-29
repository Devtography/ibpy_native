"""Unit tests for module `ibpy_native._internal._bridge`."""
# pylint: disable=protected-access
import asyncio
import datetime
import unittest
from dateutil import relativedelta

import pytz

from ibapi import contract
from ibapi import wrapper

from ibpy_native import bridge
from ibpy_native import error
from ibpy_native._internal import _global
from ibpy_native.utils import datatype
from ibpy_native.utils import finishable_queue as fq

from tests.toolkit import sample_contracts
from tests.toolkit import sample_orders
from tests.toolkit import utils

class TestGeneral(unittest.TestCase):
    """Unit tests for general/uncategorised things in `IBBridge`.

    Connection with IB is NOT required.
    """
    def setUp(self):
        self._bridge = bridge.IBBridge(host=utils.IB_HOST, port=utils.IB_PORT,
                                       client_id=utils.IB_CLIENT_ID,
                                       auto_conn=False)

    def test_set_timezone(self):
        """Test function `set_timezone`."""
        self._bridge.set_timezone(tz=pytz.timezone("Asia/Hong_Kong"))
        self.assertEqual(_global.TZ, pytz.timezone("Asia/Hong_Kong"))

        # Reset timezone to New York
        self._bridge.set_timezone(tz=pytz.timezone("America/New_York"))
        self.assertEqual(_global.TZ, pytz.timezone("America/New_York"))

    def test_set_on_notify_listener(self):
        """Test setter function `set_on_notify_listener`."""
        listener = utils.MockNotificationListener()
        code = 404
        msg = "MOCK_MSG"

        self._bridge.set_on_notify_listener(listener)
        self._bridge._wrapper.error(reqId=-1, errorCode=code, errorString=msg)

        self.assertEqual(listener.msg_code, code)
        self.assertEqual(listener.msg, msg)

class TestConnection(unittest.TestCase):
    """Unit tests for IB TWS/Gateway connection related functions in `IBBridge`.

    * Connection with IB is REQUIRED.
    """
    def test_init_0(self):
        """Test initialisation of `IBBridge`.

        * With auto connect enabled.
        """
        ib_bridge = bridge.IBBridge(host=utils.IB_HOST, port=utils.IB_PORT,
                                    client_id=utils.IB_CLIENT_ID,
                                    auto_conn=True)

        self.assertTrue(ib_bridge.is_connected)
        ib_bridge.disconnect()

    def test_init_1(self):
        """Test initialisation of `IBBridge`.

        * With auto connect disabled.
        """
        ib_bridge = bridge.IBBridge(host=utils.IB_HOST, port=utils.IB_PORT,
                                    client_id=utils.IB_CLIENT_ID,
                                    auto_conn=False)

        self.assertFalse(ib_bridge.is_connected)

    def test_connect(self):
        """Test function `connect`."""
        ib_bridge = bridge.IBBridge(host=utils.IB_HOST, port=utils.IB_PORT,
                                    client_id=utils.IB_CLIENT_ID,
                                    auto_conn=False)
        ib_bridge.connect()

        self.assertTrue(ib_bridge.is_connected)
        ib_bridge.disconnect()

    def test_disconnect(self):
        """Test function `disconnect`."""
        ib_bridge = bridge.IBBridge(host=utils.IB_HOST, port=utils.IB_PORT,
                                    client_id=utils.IB_CLIENT_ID,
                                    auto_conn=False)
        ib_bridge.connect()
        ib_bridge.disconnect()

        self.assertFalse(ib_bridge.is_connected)

class TestAccount(unittest.TestCase):
    """Unit tests for IB account related functions in `IBBridge`.

    Connection with IB is REQUIRED.
    """
    @classmethod
    def setUpClass(cls):
        cls._bridge = bridge.IBBridge(host=utils.IB_HOST, port=utils.IB_PORT,
                                      client_id=utils.IB_CLIENT_ID)

    @utils.async_test
    async def test_accounts_manager(self):
        """Test property `accounts_manager`.

        * A default `AccountsManager` should be set up and account(s) should
          be returned from IB once connected.
        """
        await asyncio.sleep(0.5)  # Wait for IB to return the account ID(s)
        self.assertTrue(self._bridge.accounts_manager.accounts)

    @utils.async_test
    async def test_req_managed_accounts(self):
        """Test function `req_managed_accouts`."""
        # Wait for IB to finish its' data return on connection
        await asyncio.sleep(0.5)
        # Clean up the already filled accounts dict
        self._bridge.accounts_manager.accounts.clear()

        self._bridge.req_managed_accounts()
        await asyncio.sleep(0.5)  # Wait for IB to return the account ID(s)
        self.assertTrue(self._bridge.accounts_manager.accounts)

    @utils.async_test
    async def test_sub_account_updates(self):
        """Test function `sub_account_updates`."""
        # Wait for IB to finish its' data return on connection
        await asyncio.sleep(0.5)
        account = self._bridge.accounts_manager.accounts[utils.IB_ACC_ID]
        await self._bridge.sub_account_updates(account)

        timeout_counter = 0
        while not account.account_ready:
            if timeout_counter == 5:
                self.fail("Test timeout as account ready status hasn't been "
                          "updated to `True` within the permitted time.")
            await asyncio.sleep(1)

        self.assertTrue(
            account.get_account_value(key="CashBalance", currency="BASE")
        )

        self._bridge._client.reqAccountUpdates(subscribe=False,
                                               acctCode=utils.IB_ACC_ID)
        self._bridge.accounts_manager.account_updates_queue.put(
            element=fq.Status.FINISHED)
        await asyncio.sleep(0.5) # Wait async tasks to finish

    @utils.async_test
    async def test_unsub_account_updates(self):
        """Test function `unsub_account_updates`."""
        # Wait for IB to finish its' data return on connection
        await asyncio.sleep(0.5)
        account = self._bridge.accounts_manager.accounts[utils.IB_ACC_ID]
        await self._bridge.unsub_account_updates(account)

        self.assertTrue(
            self._bridge.accounts_manager.account_updates_queue.finished)

    @classmethod
    def tearDownClass(cls):
        cls._bridge.disconnect()

class TestContract(unittest.TestCase):
    """Unit tests for IB contract related functions in `IBBridge`.

    Connection with IB is REQUIRED.
    """
    @classmethod
    def setUpClass(cls):
        cls._bridge = bridge.IBBridge(host=utils.IB_HOST, port=utils.IB_PORT,
                                      client_id=utils.IB_CLIENT_ID)

    @utils.async_test
    async def test_search_detailed_contracts(self):
        """Test function `search_detailed_contracts`."""
        result = await self._bridge.search_detailed_contracts(
            contract = sample_contracts.gbp_usd_fx()
        )

        self.assertTrue(result)
        self.assertNotEqual(result[0].contract.conId, 0)

    @utils.async_test
    async def test_search_detailed_contracts_err(self):
        """Test function `search_detailed_contracts`.

        * Should raise `IBError` for non-resolveable `Contract
        """
        with self.assertRaises(error.IBError):
            await self._bridge.search_detailed_contracts(
                contract = contract.Contract()
            )

    @classmethod
    def tearDownClass(cls):
        cls._bridge.disconnect()

class TestOrder(unittest.TestCase):
    """Unit tests for IB order related functions in `IBBridge`.

    Connection with IB is REQUIRED.
    """
    @classmethod
    def setUpClass(cls):
        cls._bridge = bridge.IBBridge(host=utils.IB_HOST, port=utils.IB_PORT,
                                      client_id=utils.IB_CLIENT_ID)

    def setUp(self):
        self._orders_manager = self._bridge.orders_manager

    @utils.async_test
    async def test_next_order_id(self):
        """Test function `next_order_id`."""
        self._bridge.disconnect() # To reset the orders manager
        await asyncio.sleep(0.5)
        self._bridge.connect()

        old_order_id = self._orders_manager.next_order_id
        next_order_id = await self._bridge.next_order_id()

        self.assertGreater(next_order_id, old_order_id)

    @utils.async_test
    async def test_req_open_orders(self):
        """Test function `req_open_orders`."""
        await self._bridge.req_open_orders()
        # Nothing to assert.
        # The function is good if there's no error thrown.

    @utils.async_test
    async def test_place_orders(self):
        """Test function `place_orders`."""
        # Prepare orders
        order1 = sample_orders.mkt(order_id=await self._bridge.next_order_id(),
                                   action=datatype.OrderAction.BUY)
        order2 = sample_orders.mkt(order_id=order1.orderId + 1,
                                   action=datatype.OrderAction.SELL)

        await self._bridge.place_orders(contract=sample_contracts.gbp_usd_fx(),
                                        orders=[order1, order2])
        self.assertTrue(order1.orderId in self._orders_manager.open_orders)
        self.assertTrue(order2.orderId in self._orders_manager.open_orders)
        self.assertFalse(
            self._orders_manager.is_pending_order(order_id=order1.orderId))
        self.assertFalse(
            self._orders_manager.is_pending_order(order_id=order2.orderId))

    @utils.async_test
    async def test_place_orders_err(self):
        """Test function `place_orders`.

        * Error expected due to duplicate order ID.
        """
        # Prepare orders
        order1 = sample_orders.mkt(order_id=await self._bridge.next_order_id(),
                                   action=datatype.OrderAction.BUY)
        order2 = sample_orders.mkt(order_id=order1.orderId,
                                   action=datatype.OrderAction.SELL)

        with self.assertRaises(error.IBError):
            await self._bridge.place_orders(
                contract=sample_contracts.gbp_usd_fx(),
                orders=[order1, order2]
            )
        self.assertFalse(
            self._orders_manager.is_pending_order(order_id=order1.orderId))

    @utils.async_test
    async def test_cancel_order(self):
        """Test function `cancel_order`.

        * This test will fail when the market is closed.
        """
        order = sample_orders.lmt(order_id=await self._bridge.next_order_id(),
                                  action=datatype.OrderAction.SELL,
                                  price=3)
        await self._bridge.place_orders(contract=sample_contracts.gbp_usd_fx(),
                                        orders=[order])
        self._bridge.cancel_order(order_id=order.orderId)
        await asyncio.sleep(0.5) # Give time the cancel request to arrive IB
        self.assertEqual(self._orders_manager.open_orders[order.orderId].status,
                         datatype.OrderStatus.CANCELLED)

    @classmethod
    def tearDownClass(cls):
        cls._bridge.disconnect()

class TestHistoricalData(unittest.TestCase):
    """Unit tests for historical market data related functions in `IBBridge`.

    Connection with IB is REQUIRED.

    * Tests in this suit will hang up when the market is closed.
    * Subscription of US Futures market data is REQUIRED for some tests.
    """
    @classmethod
    def setUpClass(cls):
        cls._bridge = bridge.IBBridge(host=utils.IB_HOST, port=utils.IB_PORT,
                                      client_id=utils.IB_CLIENT_ID)

    def setUp(self):
        self._end = (datetime.datetime.now() + relativedelta.relativedelta(
            weekday=relativedelta.FR(-1))
        ).replace(hour=12, minute=0, second=0, microsecond=0)
        self._start = self._end - datetime.timedelta(minutes=5)

    @utils.async_test
    async def test_get_earliest_data_point(self):
        """Test function `get_earliest_data_point`."""
        try:
            await self._bridge.get_earliest_data_point(
                contract=sample_contracts.gbp_usd_fx(),
                data_type=datatype.EarliestDataPoint.BID
            )
        except error.IBError:
            self.fail("Test fail as unexpected `IBError` raised.")

    @utils.async_test
    async def test_get_earliest_data_point_err(self):
        """Test function `get_earliest_data_point`.

        * Should raise `IBError` for invalid `Contract`.
        """
        with self.assertRaises(error.IBError):
            await self._bridge.get_earliest_data_point(
                contract=contract.Contract(),
                data_type=datatype.EarliestDataPoint.BID
            )

    @utils.async_test
    async def test_req_historical_ticks_0(self):
        """Test function `req_historical_ticks`.

        * Reqest tick data for `BID_ASK`.
        """
        async for result in self._bridge.req_historical_ticks(
            contract=sample_contracts.gbp_usd_fx(), start=self._start,
            end=self._end, tick_type=datatype.HistoricalTicks.BID_ASK,
            retry=0
        ):
            self.assertTrue(result.ticks)
            self.assertIsInstance(result.ticks[0], wrapper.HistoricalTickBidAsk)

    @utils.async_test
    async def test_req_historical_ticks_1(self):
        """Test function `req_historical_ticks`.

        * Reqest tick data for `MIDPOINT`.
        """
        async for result in self._bridge.req_historical_ticks(
            contract=sample_contracts.gbp_usd_fx(), start=self._start,
            end=self._end, tick_type=datatype.HistoricalTicks.MIDPOINT,
            retry=0
        ):
            self.assertTrue(result.ticks)
            self.assertIsInstance(result.ticks[0], wrapper.HistoricalTick)

            if result.completed:
                self.assertIsNone(result.next_start_time)

    @utils.async_test
    async def test_req_historical_ticks_2(self):
        """Test function `req_historical_ticks`.

        * Reqest tick data for `TRADES`.
        """
        async for result in self._bridge.req_historical_ticks(
            contract=sample_contracts.us_future(), start=self._start,
            end=self._end, tick_type=datatype.HistoricalTicks.TRADES,
            retry=0
        ):
            self.assertTrue(result.ticks)
            self.assertIsInstance(result.ticks[0], wrapper.HistoricalTickLast)

            if result.completed:
                self.assertIsNone(result.next_start_time)

    @utils.async_test
    async def test_req_historical_ticks_3(self):
        """Test function `req_historical_ticks`.

        * Should return `None` for the next start time as it'd be later then
          `now` for its' next iteration.
        """
        start_time = (
            (datetime.datetime.now() - datetime.timedelta(minutes=5))
            .astimezone(_global.TZ)
            .replace(second=0, microsecond=0, tzinfo=None)
        )
        async for result in self._bridge.req_historical_ticks(
            contract=sample_contracts.us_future_next(), start=start_time,
            tick_type=datatype.HistoricalTicks.TRADES,
            retry=0
        ):
            if result.completed:
                self.assertIsNone(result.next_start_time)

    @utils.async_test
    async def test_req_historical_ticks_err_0(self):
        """Test function `req_historical_ticks`.

        * Expect `ValueError` due to value of `start` is an aware datetime
          object.
        """
        with self.assertRaises(ValueError):
            async for _ in self._bridge.req_historical_ticks(
                contract=sample_contracts.gbp_usd_fx(),
                start=_global.TZ.localize(self._start), end=self._end,
                tick_type=datatype.HistoricalTicks.BID_ASK, retry=0
            ):
                pass

    @utils.async_test
    async def test_req_historical_ticks_err_1(self):
        """Test function `req_historical_ticks`.

        * Expect `ValueError` due to value of `end` is an aware datetime
          object.
        """
        with self.assertRaises(ValueError):
            async for _ in self._bridge.req_historical_ticks(
                contract=sample_contracts.gbp_usd_fx(),
                start=self._start, end=_global.TZ.localize(self._end),
                tick_type=datatype.HistoricalTicks.BID_ASK, retry=0
            ):
                pass

    @utils.async_test
    async def test_req_historical_ticks_err_2(self):
        """Test function `req_historical_ticks`.

        * Expect `ValueError` due to value of `end` is an aware datetime
          object.
        """
        with self.assertRaises(ValueError):
            async for _ in self._bridge.req_historical_ticks(
                contract=sample_contracts.gbp_usd_fx(),
                start=self._start, end=self._end,
                tick_type=datatype.HistoricalTicks.BID_ASK,
                daily_data_starting_point=datetime.time(
                    hour=17, minute=0, tzinfo=_global.TZ),
                retry=0
            ):
                pass

    @utils.async_test
    async def test_req_historical_ticks_err_3(self):
        """Test function `req_historical_ticks`.

        * Expect `IBError` due to unresolvable `Contract`.
        """
        with self.assertRaises(error.IBError):
            async for _ in self._bridge.req_historical_ticks(
                contract=contract.Contract(), start=self._start, end=self._end,
                tick_type=datatype.HistoricalTicks.BID_ASK, retry=0
            ):
                pass

    @utils.async_test
    async def test_req_historical_ticks_err_4(self):
        """Test function `req_historical_ticks`.

        * Expect `IBError` due to IB returning an error
        """
        with self.assertRaises(error.IBError):
            async for _ in self._bridge.req_historical_ticks(
                contract=sample_contracts.gbp_usd_fx(), start=self._start,
                end=self._end, tick_type=datatype.HistoricalTicks.TRADES,
                retry=0
            ):
                pass

    @classmethod
    def tearDownClass(cls):
        cls._bridge.disconnect()

class TestLiveData(unittest.TestCase):
    """Unit tests for live market data related functions in `IBBridge`.

    Connection with IB is REQUIRED.

    * Tests in this suit will hang up when the market is closed.
    * Subscription of US Futures market data is REQUIRED for some tests.
    """
    @classmethod
    def setUpClass(cls):
        cls._bridge = bridge.IBBridge(host=utils.IB_HOST, port=utils.IB_PORT,
                                      client_id=utils.IB_CLIENT_ID)

    def setUp(self):
        self._listener = utils.MockLiveTicksListener()

    @utils.async_test
    async def test_stream_live_ticks_0(self):
        """Test function `stream_live_ticks`.

        * Request tick data for `BID_ASK`.
        """
        req_id = await self._bridge.stream_live_ticks(
            contract=sample_contracts.gbp_usd_fx(), listener=self._listener,
            tick_type=datatype.LiveTicks.BID_ASK
        )

        while not self._listener.ticks:
            await asyncio.sleep(0.5)

        self.assertIsInstance(self._listener.ticks[0],
                              wrapper.HistoricalTickBidAsk)

        self._bridge._client.cancel_live_ticks_stream(req_id)
        await asyncio.sleep(0.5)

    @utils.async_test
    async def test_stream_live_ticks_1(self):
        """Test function `stream_live_ticks`.

        * Request tick data for `MIDPOINT`.
        """
        req_id = await self._bridge.stream_live_ticks(
            contract=sample_contracts.gbp_usd_fx(), listener=self._listener,
            tick_type=datatype.LiveTicks.MIDPOINT
        )

        while not self._listener.ticks:
            await asyncio.sleep(0.5)

        self.assertIsInstance(self._listener.ticks[0], wrapper.HistoricalTick)

        self._bridge._client.cancel_live_ticks_stream(req_id)
        await asyncio.sleep(0.5)

    @utils.async_test
    async def test_stream_live_ticks_2(self):
        """Test function `stream_live_ticks`.

        * Request tick data for `ALL_LAST`.
        """
        req_id = await self._bridge.stream_live_ticks(
            contract=sample_contracts.us_future(), listener=self._listener,
            tick_type=datatype.LiveTicks.ALL_LAST
        )

        while not self._listener.ticks:
            await asyncio.sleep(0.5)

        self.assertIsInstance(self._listener.ticks[0],
                              wrapper.HistoricalTickLast)

        self._bridge._client.cancel_live_ticks_stream(req_id)
        await asyncio.sleep(0.5)

    @utils.async_test
    async def test_stream_live_ticks_3(self):
        """Test function `stream_live_ticks`.

        * Request tick data for `LAST`.
        """
        req_id = await self._bridge.stream_live_ticks(
            contract=sample_contracts.us_future(), listener=self._listener,
            tick_type=datatype.LiveTicks.LAST
        )

        while not self._listener.ticks:
            await asyncio.sleep(0.5)

        self.assertIsInstance(self._listener.ticks[0],
                              wrapper.HistoricalTickLast)

        self._bridge._client.cancel_live_ticks_stream(req_id)
        await asyncio.sleep(0.5)

    @utils.async_test
    async def test_stop_live_ticks_stream(self):
        """Test function `stop_live_ticks_stream`."""
        req_id = await self._bridge.stream_live_ticks(
            contract=sample_contracts.gbp_usd_fx(), listener=self._listener,
            tick_type=datatype.LiveTicks.BID_ASK
        )
        await asyncio.sleep(0.5)

        self._bridge.stop_live_ticks_stream(stream_id=req_id)
        await asyncio.sleep(0.5)
        self.assertTrue(self._listener.finished)

    def test_stop_live_ticks_stream_err(self):
        """Test function `stop_live_ticks_stream`.

        * Should raise `IBError` as stream ID 0 has no stream associated with
          it.
        """
        with self.assertRaises(error.IBError):
            self._bridge.stop_live_ticks_stream(stream_id=0)

    @classmethod
    def tearDownClass(cls):
        cls._bridge.disconnect()
