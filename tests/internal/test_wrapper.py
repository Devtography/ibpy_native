"""Unit tests for module `ibpy_native._internal._wrapper`."""
# pylint: disable=protected-access
import asyncio
import datetime
import threading
import unittest

from ibapi import contract
from ibapi import wrapper

from ibpy_native import error
from ibpy_native import models
from ibpy_native import manager
from ibpy_native._internal import _client
from ibpy_native._internal import _global
from ibpy_native._internal import _wrapper
from ibpy_native.utils import datatype
from ibpy_native.utils import finishable_queue as fq

from tests.toolkit import sample_contracts
from tests.toolkit import sample_orders
from tests.toolkit import utils

class TestGeneral(unittest.TestCase):
    """Unit tests for general/uncategorised things in `IBWrapper`.

    * Connection with IB is NOT required.
    """
    def setUp(self):
        self._wrapper = _wrapper.IBWrapper(
            client_id=utils.IB_CLIENT_ID,
            accounts_manager=utils.MockAccountsManagementDelegate(),
            orders_manager=manager.OrdersManager()
        )

    def test_set_on_notify_listener(self):
        """Test setter `set_on_notify_listener` & overridden function `error`
        for the delivery of IB system notification.

        * Expect to receive IB's system notification (`reqId` -1) once the
        notification listener is set.
        """
        code = 1001
        msg = "MOCK MSG"
        listener = utils.MockNotificationListener()

        self._wrapper.set_on_notify_listener(listener)
        # Mock IB system notification
        self._wrapper.error(reqId=-1, errorCode=code, errorString=msg)
        # Notification should have received by the notification listener
        self.assertEqual(listener.msg_code, code)
        self.assertEqual(listener.msg, msg)

    @utils.async_test
    async def test_error(self):
        """Test overridden function `error`."""
        req_id = 1
        code = 404
        msg = "ERROR"
        # Prepare request queue
        queue = self._wrapper.get_request_queue(req_id)
        # Mock IB error
        self._wrapper.error(reqId=req_id, errorCode=code, errorString=msg)
        queue.put(element=fq.Status.FINISHED)
        result = await queue.get()
        # Expect exception of `IBError` to be sent to corresponding request
        # queue.
        self.assertIsInstance(result[0], error.IBError)
        self.assertEqual(result[0].err_code, code)
        self.assertEqual(result[0].err_str, msg)

class TestConnectionEvents(unittest.TestCase):
    """Unit tests for connection events related mechanism implemented in
    `IBWrapper`.

    * Connection with IB is NOT REQUIRED.
    """
    def setUp(self):
        self._listener = utils.MockConnectionListener()
        self._wrapper = _wrapper.IBWrapper(
            client_id=utils.IB_CLIENT_ID,
            accounts_manager=utils.MockAccountsManagementDelegate(),
            orders_manager=manager.OrdersManager(),
            connection_listener=self._listener
        )

    def test_on_connected(self):
        """Test the event of connection established."""
        # Mock the behaviour of initial handshake callback once the connection
        # is made.
        self._wrapper.nextValidId(orderId=1)

        self.assertTrue(self._listener.connected)

    def test_on_disconnected(self):
        """Test the event of connection dropped."""
        # Mock the `NOT_CONNECTED` error is returned to `error` callback
        self._wrapper.error(reqId=-1, errorCode=error.IBErrorCode.NOT_CONNECTED,
                            errorString=_global.MSG_NOT_CONNECTED)

        self.assertFalse(self._listener.connected)

class TestReqQueue(unittest.TestCase):
    """Unit tests for `_req_queue` related mechanicisms in `IBWrapper`.

    Connection with IB is NOT required.
    """
    def setUp(self):
        self._wrapper = _wrapper.IBWrapper(
            client_id=utils.IB_CLIENT_ID,
            accounts_manager=utils.MockAccountsManagementDelegate(),
            orders_manager=manager.OrdersManager()
        )

        self._init_id = utils.IB_CLIENT_ID * 1000

    def test_next_req_id_0(self):
        """Test property `next_req_id` for retrieval of next usable
        request ID.

        * No ID has been occupied yet.
        """
        # 1st available request ID should always be initial request ID
        self.assertEqual(self._wrapper.next_req_id, self._init_id)

    def test_next_req_id_1(self):
        """Test property `next_req_id` for retrieval of next usable
        request ID.

        * Initial request ID has already been occupied.
        """
        # Occupy request ID `CLIENT_ID * 1000`
        self._wrapper.get_request_queue(req_id=self._init_id)
        # Next available request ID should be `CLIENT_ID * 1000 + 1`
        self.assertEqual(self._wrapper.next_req_id, self._init_id + 1)

    @utils.async_test
    async def test_next_req_id_2(self):
        """Test property `next_req_id` for retrieval of next usable
        request ID.

        * Initial request ID was occupied but released for reuse.
        """
        # Occupy initial request ID
        queue = self._wrapper.get_request_queue(req_id=self._init_id)
        # Release initial request ID by marking the queue associated as FINISHED
        queue.put(element=fq.Status.FINISHED)
        await queue.get()
        # Next available request ID should reuse initial request ID
        self.assertEqual(self._wrapper.next_req_id, self._init_id)

    def test_get_request_queue_0(self):
        """Test getter `get_request_queue`."""
        try:
            self._wrapper.get_request_queue(req_id=1)
        except error.IBError:
            self.fail("IBError raised unexpectedly.")

    @utils.async_test
    async def test_get_request_queue_1(self):
        """Test getter `get_request_queue`.

        * Queue associated with ID 1 has already been initialised and available
        for reuse. Should return the same `FinishableQueue` instance.
        """
        # Prepare queue with request ID 1
        queue = self._wrapper.get_request_queue(req_id=1)
        queue.put(element=fq.Status.FINISHED)
        await queue.get()
        # Should return the same `FinishableQueue` instance for reuse
        self.assertEqual(self._wrapper.get_request_queue(req_id=1), queue)

    def test_get_request_queue_err(self):
        """Test getter `get_request_queue` for error case.

        * Queue associated with ID 1 has already been initialised and NOT
        ready for reuse. Should raise exception `IBError`.
        """
        # Prepare queue with request ID 1
        self._wrapper.get_request_queue(req_id=1)
        # Expect exception `IBError`
        with self.assertRaises(error.IBError):
            self._wrapper.get_request_queue(req_id=1)

    def test_get_request_queue_no_throw_0(self):
        """Test getter `get_request_queue_no_throw`.

        * No queue has been initialised before. Should return `None`.
        """
        self.assertEqual(self._wrapper.get_request_queue_no_throw(req_id=1),
                         None)

    def test_get_request_queue_no_throw_1(self):
        """Test getter `get_request_queue_no_throw`.

        * Queue associated with ID 1 has already been initialised. Should
        return the same `FinishableQueue` instance even if it's not ready for
        reuse yet.
        """
        # Prepare queue with request ID 1
        queue = self._wrapper.get_request_queue(req_id=1)
        # Expect the same `FinishableQueue` instance.
        self.assertEqual(self._wrapper.get_request_queue_no_throw(req_id=1),
                         queue)

class TestAccountAndPortfolio(unittest.TestCase):
    """Unit tests for account and portfolio data related functions in
    `IBWrapper`.

    Connection with IB is NOT required.
    """
    def setUp(self):
        self._delegate = utils.MockAccountsManagementDelegate()
        self._wrapper = _wrapper.IBWrapper(
            client_id=utils.IB_CLIENT_ID,
            accounts_manager=self._delegate,
            orders_manager=manager.OrdersManager()
        )


    def test_managed_accounts(self):
        """Test overridden function `managedAccounts`."""
        # Mock accounts list received from IB
        acc_1 = "DU0000140"
        acc_2 = "DU0000141"
        # IB accounts list format "DU0000140,DU0000141,..."
        self._wrapper.managedAccounts(accountsList=f"{acc_1},{acc_2}")
        # Expect instances of model `Accounts` for `acc_1` & `acc_2`
        # to be stored in the `AccountsManagementDelegate` instance.
        self.assertTrue(self._delegate.accounts)
        self.assertTrue(acc_1 in self._delegate.accounts)
        self.assertTrue(acc_2 in self._delegate.accounts)

    @utils.async_test
    async def test_update_account_value(self):
        """Test overridden function `updateAccountValue`."""
        # Mock account value data received from IB
        self._wrapper.updateAccountValue(
            key="AvailableFunds", val="890622.47",
            currency="USD", accountName="DU0000140"
        )
        self._delegate.account_updates_queue.put(element=fq.Status.FINISHED)
        result = await self._delegate.account_updates_queue.get()
        # Expect instance of `RawAccountValueData` in `account_updates_queue`
        self.assertIsInstance(result[0], models.RawAccountValueData)

    @utils.async_test
    async def test_update_portfolio(self):
        """Test overridden function `updatePortfolio`."""
        # Mock portfolio data received from IB
        self._wrapper.updatePortfolio(
            contract=sample_contracts.gbp_usd_fx(), position=1000,
            marketPrice=1.38220, marketValue=1382.2, averageCost=1.33327,
            unrealizedPNL=48.93, realizedPNL=0, accountName="DU0000140"
        )
        self._delegate.account_updates_queue.put(element=fq.Status.FINISHED)
        results = await self._delegate.account_updates_queue.get()
        # Expect instance of `RawPortfolioData` in `account_updates_queue`
        self.assertIsInstance(results[0], models.RawPortfolioData)

    @utils.async_test
    async def test_update_account_time(self):
        """Test overridden function `updateAccountTime`."""
        # Mock last update system time received from IB
        time = "09:30"
        self._wrapper.updateAccountTime(timeStamp=time)
        self._delegate.account_updates_queue.put(element=fq.Status.FINISHED)
        results = await self._delegate.account_updates_queue.get()
        # Expect data stored as-is in `account_updates_queue`
        self.assertEqual(results[0], time)

class TestOrder(unittest.TestCase):
    """Unit tests for IB order related functions & properties in `IBWrapper`.

    Connection with IB is REQUIRED.
    """
    @classmethod
    def setUpClass(cls):
        cls._wrapper = _wrapper.IBWrapper(
            client_id=utils.IB_CLIENT_ID,
            accounts_manager=utils.MockAccountsManagementDelegate(),
            orders_manager=manager.OrdersManager()
        )
        cls._client = _client.IBClient(cls._wrapper)

        cls._client.connect(utils.IB_HOST, utils.IB_PORT, utils.IB_CLIENT_ID)

        thread = threading.Thread(target=cls._client.run)
        thread.start()

    def setUp(self):
        self._orders_manager = self._wrapper.orders_manager

    @utils.async_test
    async def test_open_order(self):
        """Test overridden function `openOrder`."""
        order_id = await self._client.req_next_order_id()
        self._client.placeOrder(
            orderId=order_id, contract=sample_contracts.gbp_usd_fx(),
            order=sample_orders.mkt(order_id=order_id,
                                    action=datatype.OrderAction.BUY)
        )
        await asyncio.sleep(1)

        self.assertTrue(order_id in self._orders_manager.open_orders)

    @utils.async_test
    async def test_open_order_end(self):
        """Test overridden function `openOrderEnd`."""
        queue = self._wrapper.get_request_queue(req_id=_global.IDX_OPEN_ORDERS)
        self._client.reqOpenOrders()
        await queue.get()

        self.assertTrue(queue.finished)

    @utils.async_test
    async def test_order_status(self):
        """Test overridden function `orderStatus`."""
        order_id = await self._client.req_next_order_id()
        self._client.placeOrder(
            orderId=order_id, contract=sample_contracts.gbp_usd_fx(),
            order=sample_orders.mkt(order_id=order_id,
                                    action=datatype.OrderAction.SELL)
        )
        await asyncio.sleep(1)

        self.assertTrue(self._orders_manager.open_orders[order_id].exec_rec)

    @classmethod
    def tearDownClass(cls):
        cls._client.disconnect()

class TestContract(unittest.TestCase):
    """Unit tests for IB contract related functions in `IBWrapper`.

    Connection with IB is REQUIRED.
    """
    @classmethod
    def setUpClass(cls):
        cls._wrapper = _wrapper.IBWrapper(
            client_id=utils.IB_CLIENT_ID,
            accounts_manager=utils.MockAccountsManagementDelegate(),
            orders_manager=manager.OrdersManager()
        )
        cls._client = _client.IBClient(cls._wrapper)

        cls._client.connect(utils.IB_HOST, utils.IB_PORT, utils.IB_CLIENT_ID)

        thread = threading.Thread(target=cls._client.run)
        thread.start()

    @utils.async_test
    async def test_contract_details(self):
        """Test overridden function `contractDetails`.

        * `contractDetailsEnd` will be invoked after `contractDetails`.
        """
        req_id = self._wrapper.next_req_id
        queue = self._wrapper.get_request_queue(req_id)

        self._client.reqContractDetails(reqId=req_id,
                                        contract=sample_contracts.gbp_usd_fx())
        await asyncio.sleep(0.5)
        result = await queue.get()

        self.assertTrue(result) # Expect item from queue
        # Expect the resolved `ContractDetails` object to be returned
        self.assertIsInstance(result[0], contract.ContractDetails)

    @utils.async_test
    async def test_contract_details_end(self):
        """Test overridden function `contractDetailsEnd`."""
        req_id = self._wrapper.next_req_id
        queue = self._wrapper.get_request_queue(req_id)

        self._wrapper.contractDetailsEnd(reqId=req_id)
        await queue.get()

        self.assertTrue(queue.finished) # Expect the queue to be marked as FINISHED

    @classmethod
    def tearDownClass(cls):
        cls._client.disconnect()

class TestHistoricalData(unittest.TestCase):
    """Unit tests for historical market data related functions in `IBWrapper`.

    Connection with IB is REQUIRED.
    """
    @classmethod
    def setUpClass(cls):
        cls._wrapper = _wrapper.IBWrapper(
            client_id=utils.IB_CLIENT_ID,
            accounts_manager=utils.MockAccountsManagementDelegate(),
            orders_manager=manager.OrdersManager()
        )
        cls._client = _client.IBClient(cls._wrapper)

        cls._client.connect(utils.IB_HOST, utils.IB_PORT, utils.IB_CLIENT_ID)

        thread = threading.Thread(target=cls._client.run)
        thread.start()

    def setUp(self):
        self._req_id = self._wrapper.next_req_id
        self._queue = self._wrapper.get_request_queue(req_id=self._req_id)

    @utils.async_test
    async def test_head_timestamp(self):
        """Test overridden function `headTimestamp`."""
        timestamp = "1110342600" # Unix timestamp
        # Mock timestamp received from IB
        self._wrapper.headTimestamp(reqId=self._req_id, headTimestamp=timestamp)
        result = await self._queue.get()

        self.assertTrue(result) # Expect item from queue
        self.assertEqual(result[0], timestamp)  # Expect data received as-is
        # Expect queue to be marked as FINISHED
        self.assertTrue(self._queue.finished)

    @utils.async_test
    async def test_historical_ticks(self):
        """Test overridden function `historicalTicks`."""
        end = (datetime.datetime.now().astimezone(_global.TZ)
               .strftime(_global.TIME_FMT))

        self._client.reqHistoricalTicks(
            reqId=self._req_id, contract=sample_contracts.gbp_usd_fx(),
            startDateTime="", endDateTime=end, numberOfTicks=1000,
            whatToShow=datatype.HistoricalTicks.MIDPOINT.value, useRth=1,
            ignoreSize=False, miscOptions=[]
        )
        result = await self._queue.get()

        self.assertTrue(result)  # Expect item from queue
        # Expect `ListOfHistoricalTick` to be sent to the queue
        self.assertIsInstance(result[0], wrapper.ListOfHistoricalTick)
        # Expect queue to be marked as FINISHED
        self.assertTrue(self._queue.finished)

    @utils.async_test
    async def test_historical_ticks_bid_ask(self):
        """Test overridden function `historicalTicksBidAsk`."""
        end = (datetime.datetime.now().astimezone(_global.TZ)
               .strftime(_global.TIME_FMT))

        self._client.reqHistoricalTicks(
            reqId=self._req_id, contract=sample_contracts.gbp_usd_fx(),
            startDateTime="", endDateTime=end, numberOfTicks=1000,
            whatToShow=datatype.HistoricalTicks.BID_ASK.value, useRth=1,
            ignoreSize=False, miscOptions=[]
        )
        result = await self._queue.get()

        self.assertTrue(result)  # Expect item from queue
        # Expect `ListOfHistoricalTick` to be sent to the queue
        self.assertIsInstance(result[0], wrapper.ListOfHistoricalTickBidAsk)
        # Expect queue to be marked as FINISHED
        self.assertTrue(self._queue.finished)

    @utils.async_test
    async def test_historical_ticks_last(self):
        """Test overridden function `historicalTicksLast`."""
        end = (datetime.datetime.now().astimezone(_global.TZ)
               .strftime(_global.TIME_FMT))

        self._client.reqHistoricalTicks(
            reqId=self._req_id, contract=sample_contracts.gbp_usd_fx(),
            startDateTime="", endDateTime=end, numberOfTicks=1000,
            whatToShow=datatype.HistoricalTicks.TRADES.value, useRth=1,
            ignoreSize=False, miscOptions=[]
        )
        result = await self._queue.get()

        self.assertTrue(result)  # Expect item from queue
        # Expect `ListOfHistoricalTick` to be sent to the queue
        self.assertIsInstance(result[0], wrapper.ListOfHistoricalTickLast)
        # Expect queue to be marked as FINISHED
        self.assertTrue(self._queue.finished)

    @classmethod
    def tearDownClass(cls):
        cls._client.disconnect()

class TestTickByTickData(unittest.TestCase):
    """Unit tests for Tick-by-Tick data related functions in `IBWrapper`.

    Connection with IB is REQUIRED.

    * Tests in this suit will hang up when the market is closed.
    * Subscription of US Futures market data is REQUIRED for some tests.
    """
    @classmethod
    def setUpClass(cls):
        cls._wrapper = _wrapper.IBWrapper(
            client_id=utils.IB_CLIENT_ID,
            accounts_manager=utils.MockAccountsManagementDelegate(),
            orders_manager=manager.OrdersManager()
        )
        cls._client = _client.IBClient(cls._wrapper)

        cls._client.connect(utils.IB_HOST, utils.IB_PORT, utils.IB_CLIENT_ID)

        thread = threading.Thread(target=cls._client.run)
        thread.start()

    def setUp(self):
        self._received = False # Indicates if tick received
        self._req_id = self._wrapper.next_req_id
        self._queue = self._wrapper.get_request_queue(req_id=self._req_id)

    @utils.async_test
    async def test_tick_by_tick_all_last_0(self):
        """Test overridden function `tickByTickAllLast` with tick type `Last`.
        """
        self._client.reqTickByTickData(
            reqId=self._req_id, contract=sample_contracts.us_future(),
            tickType=datatype.LiveTicks.LAST.value, numberOfTicks=0,
            ignoreSize=True
        )

        async for elem in self._queue.stream():
            if elem is fq.Status.FINISHED:
                continue # Let the async task finish
            if not self._received:
                # Expect `HistoricalTickLast` to be sent to queue
                self.assertIsInstance(elem, wrapper.HistoricalTickLast)
                await self._stop_streaming(req_id=self._req_id)

    @utils.async_test
    async def test_tick_by_tick_all_last_1(self):
        """Test overridden function `tickByTickAllLast` with tick type
        `AllLast`.
        """
        self._client.reqTickByTickData(
            reqId=self._req_id, contract=sample_contracts.us_future(),
            tickType=datatype.LiveTicks.ALL_LAST.value, numberOfTicks=0,
            ignoreSize=True
        )

        async for elem in self._queue.stream():
            if elem is fq.Status.FINISHED:
                continue # Let the async task finish
            if not self._received:
                # Expect `HistoricalTickLast` to be sent to queue
                self.assertIsInstance(elem, wrapper.HistoricalTickLast)
                await self._stop_streaming(req_id=self._req_id)


    @utils.async_test
    async def test_tick_by_tick_bid_ask(self):
        """Test overridden function `tickByTickBidAsk`."""
        self._client.reqTickByTickData(
            reqId=self._req_id, contract=sample_contracts.gbp_usd_fx(),
            tickType=datatype.LiveTicks.BID_ASK.value, numberOfTicks=0,
            ignoreSize=True
        )

        async for elem in self._queue.stream():
            if elem is fq.Status.FINISHED:
                continue # Let the async task finish
            if not self._received:
                # Expect `HistoricalTickLast` to be sent to queue
                self.assertIsInstance(elem, wrapper.HistoricalTickBidAsk)
                await self._stop_streaming(req_id=self._req_id)

    @utils.async_test
    async def test_tick_by_tick_mid_point(self):
        """Test overridden function `tickByTickMidPoint`."""
        self._client.reqTickByTickData(
            reqId=self._req_id, contract=sample_contracts.gbp_usd_fx(),
            tickType=datatype.LiveTicks.MIDPOINT.value, numberOfTicks=0,
            ignoreSize=True
        )

        async for elem in self._queue.stream():
            if elem is fq.Status.FINISHED:
                continue # Let the async task finish
            if not self._received:
                # Expect `HistoricalTickLast` to be sent to queue
                self.assertIsInstance(elem, wrapper.HistoricalTick)
                await self._stop_streaming(req_id=self._req_id)

    @classmethod
    def tearDownClass(cls):
        cls._client.disconnect()

    async def _stop_streaming(self, req_id: int):
        self._received = True
        self._client.cancelTickByTickData(reqId=req_id)
        await asyncio.sleep(2)
        self._queue.put(element=fq.Status.FINISHED)
