"""Unit tests for module `ibpy_native.wrapper`."""
# pylint: disable=protected-access
import asyncio
import enum
import os
import threading
import unittest

from ibapi import wrapper as ib_wrapper

from ibpy_native import models
from ibpy_native.interfaces import listeners
from ibpy_native.internal import client as ibpy_client
from ibpy_native.internal import wrapper as ibpy_wrapper
from ibpy_native.utils import finishable_queue as fq

from tests.toolkit import sample_contracts
from tests.toolkit import utils

class Const(enum.IntEnum):
    """Predefined constants for `TestIBWrapper`."""
    RID_RESOLVE_CONTRACT = 43
    RID_FETCH_HISTORICAL_TICKS = 18001
    RID_REQ_TICK_BY_TICK_DATA_ALL_LAST = 19001
    RID_REQ_TICK_BY_TICK_DATA_LAST = 19002
    RID_REQ_TICK_BY_TICK_DATA_MIDPOINT = 19003
    RID_REQ_TICK_BY_TICK_DATA_BIDASK = 19004
    QUEUE_MAX_WAIT_SEC = 10

class TestIBWrapper(unittest.TestCase):
    """Unit tests for class `_IBWrapper`."""

    @classmethod
    def setUpClass(cls):
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

    # _IBWrapper specifics
    @utils.async_test
    async def test_next_req_id(self):
        """Test retrieval of next usable request ID."""
        # Prepare the `_FinishableQueue` objects in internal `__req_queue`
        self._wrapper._req_queue.clear()
        _ = self._wrapper.get_request_queue(req_id=0)
        f_queue = self._wrapper.get_request_queue(req_id=1)
        _ = self._wrapper.get_request_queue(req_id=10)

        self.assertEqual(self._wrapper.next_req_id, 11)

        f_queue.put(element=fq._Status.FINISHED)
        await f_queue.get()
        self.assertEqual(self._wrapper.next_req_id, 1)

    def test_notification_listener(self):
        """Test notification listener approach."""
        class MockListener(listeners.NotificationListener):
            """Mock notification listener."""
            triggered = False

            def on_notify(self, msg_code: int, msg: str):
                """Mock callback implementation
                """
                print(f"{msg_code} - {msg}")

                self.triggered = True

        mock_listener = MockListener()

        self._wrapper.set_on_notify_listener(listener=mock_listener)
        self._wrapper.error(reqId=-1, errorCode=1100, errorString="MOCK MSG")

        self.assertTrue(mock_listener.triggered)

    # Historical market data
    @utils.async_test
    async def test_historical_ticks(self):
        """Test overridden function `historicalTicks`."""
        end_time = "20200327 16:30:00"

        f_queue = self._wrapper.get_request_queue(
            req_id=Const.RID_FETCH_HISTORICAL_TICKS
        )

        self._client.reqHistoricalTicks(
            reqId=Const.RID_FETCH_HISTORICAL_TICKS.value,
            contract=sample_contracts.gbp_usd_fx(),
            startDateTime="", endDateTime=end_time,
            numberOfTicks=1000, whatToShow="MIDPOINT", useRth=1,
            ignoreSize=False, miscOptions=[]
        )

        result = await f_queue.get()

        self.assertEqual(f_queue.status, fq._Status.FINISHED)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], ib_wrapper.ListOfHistoricalTick)

    @utils.async_test
    async def test_historical_ticks_bid_ask(self):
        """Test overridden function `historicalTicksBidAsk`."""
        end_time = "20200327 16:30:00"

        f_queue = self._wrapper.get_request_queue(
            req_id=Const.RID_FETCH_HISTORICAL_TICKS
        )

        self._client.reqHistoricalTicks(
            reqId=Const.RID_FETCH_HISTORICAL_TICKS.value,
            contract=sample_contracts.gbp_usd_fx(),
            startDateTime="", endDateTime=end_time,
            numberOfTicks=1000, whatToShow="BID_ASK", useRth=1,
            ignoreSize=False, miscOptions=[]
        )

        result = await f_queue.get()

        self.assertEqual(f_queue.status, fq._Status.FINISHED)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], ib_wrapper.ListOfHistoricalTickBidAsk)

    @utils.async_test
    async def test_historical_ticks_last(self):
        """Test overridden function `historicalTicksLast`."""
        end_time = "20200327 16:30:00"

        f_queue = self._wrapper.get_request_queue(
            req_id=Const.RID_FETCH_HISTORICAL_TICKS
        )

        self._client.reqHistoricalTicks(
            reqId=Const.RID_FETCH_HISTORICAL_TICKS.value,
            contract=sample_contracts.gbp_usd_fx(),
            startDateTime="", endDateTime=end_time,
            numberOfTicks=1000, whatToShow="TRADES", useRth=1,
            ignoreSize=False, miscOptions=[]
        )

        result = await f_queue.get()

        self.assertEqual(f_queue.status, fq._Status.FINISHED)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], ib_wrapper.ListOfHistoricalTickLast)

    @utils.async_test
    async def test_tick_by_tick_all_last(self):
        """Test overridden function `tickByTickAllLast`."""
        f_queue = self._wrapper.get_request_queue(
            req_id=Const.RID_REQ_TICK_BY_TICK_DATA_ALL_LAST
        )

        self._client.reqTickByTickData(
            reqId=Const.RID_REQ_TICK_BY_TICK_DATA_ALL_LAST.value,
            contract=sample_contracts.us_future(),
            tickType='AllLast',
            numberOfTicks=0,
            ignoreSize=True
        )

        async for ele in f_queue.stream():
            self.assertIsInstance(ele,
                                  (ib_wrapper.HistoricalTickLast, fq._Status))
            self.assertIsNot(ele, fq._Status.ERROR)

            if ele is not fq._Status.FINISHED:
                self._client.cancelTickByTickData(
                    reqId=Const.RID_REQ_TICK_BY_TICK_DATA_ALL_LAST.value
                )

                f_queue.put(element=fq._Status.FINISHED)

    @utils.async_test
    async def test_tick_by_tick_last(self):
        """Test overridden function `tickByTickAllLast` with tick type `Last`.
        """
        f_queue = self._wrapper.get_request_queue(
            req_id=Const.RID_REQ_TICK_BY_TICK_DATA_LAST
        )

        self._client.reqTickByTickData(
            reqId=Const.RID_REQ_TICK_BY_TICK_DATA_LAST.value,
            contract=sample_contracts.us_future(),
            tickType='Last',
            numberOfTicks=0,
            ignoreSize=True
        )

        async for ele in f_queue.stream():
            self.assertIsInstance(ele,
                                  (ib_wrapper.HistoricalTickLast, fq._Status))
            self.assertIsNot(ele, fq._Status.ERROR)

            if ele is not fq._Status.FINISHED:
                self._client.cancelTickByTickData(
                    reqId=Const.RID_REQ_TICK_BY_TICK_DATA_LAST.value
                )

                f_queue.put(element=fq._Status.FINISHED)


    @utils.async_test
    async def test_tick_by_tick_bid_ask(self):
        """Test overridden function `tickByTickBidAsk`."""
        f_queue = self._wrapper.get_request_queue(
            req_id=Const.RID_REQ_TICK_BY_TICK_DATA_BIDASK
        )

        self._client.reqTickByTickData(
            reqId=Const.RID_REQ_TICK_BY_TICK_DATA_BIDASK.value,
            contract=sample_contracts.gbp_usd_fx(),
            tickType='BidAsk',
            numberOfTicks=0,
            ignoreSize=True
        )

        async for ele in f_queue.stream():
            self.assertIsInstance(ele,
                                  (ib_wrapper.HistoricalTickBidAsk, fq._Status))
            self.assertIsNot(ele, fq._Status.ERROR)

            if ele is not fq._Status.FINISHED:
                self._client.cancelTickByTickData(
                    reqId=Const.RID_REQ_TICK_BY_TICK_DATA_BIDASK.value
                )

                f_queue.put(element=fq._Status.FINISHED)

    @utils.async_test
    async def test_tick_by_tick_mid_point(self):
        """Test overridden function `tickByTickMidPoint`."""
        f_queue = self._wrapper.get_request_queue(
            req_id=Const.RID_REQ_TICK_BY_TICK_DATA_MIDPOINT
        )

        self._client.reqTickByTickData(
            reqId=Const.RID_REQ_TICK_BY_TICK_DATA_MIDPOINT.value,
            contract=sample_contracts.gbp_usd_fx(),
            tickType='MidPoint',
            numberOfTicks=0,
            ignoreSize=True
        )

        async for ele in f_queue.stream():
            self.assertIsInstance(ele,
                                  (ib_wrapper.HistoricalTick, fq._Status))
            self.assertIsNot(ele, fq._Status.ERROR)

            if ele is not fq._Status.FINISHED:
                self._client.cancelTickByTickData(
                    reqId=Const.RID_REQ_TICK_BY_TICK_DATA_MIDPOINT.value
                )

                f_queue.put(element=fq._Status.FINISHED)

    @classmethod
    def tearDownClass(cls):
        cls._client.disconnect()

class TestAccountAndPortfolioData(unittest.TestCase):
    """Unit tests for account and portfolio data related callbacks & functions
    in class `ibpy_native.internal.wrapper._IBWrapper`.

    Connection with IB Gateway is required for this test suit.
    """
    @classmethod
    def setUpClass(cls):
        cls.wrapper = ibpy_wrapper._IBWrapper()
        cls.client = ibpy_client._IBClient(cls.wrapper)

        cls.client.connect(
            os.getenv('IB_HOST', '127.0.0.1'),
            int(os.getenv('IB_PORT', '4002')),
            1001
        )

        thread = threading.Thread(target=cls.client.run)
        thread.start()

        setattr(cls.client, "_thread", thread)

    def setUp(self):
        self.mock_delegate = utils.MockAccountManagementDelegate()
        self.wrapper.set_account_management_delegate(self.mock_delegate)

    def test_account_management_delegate(self):
        """Test `_AccountManagementDelegate` implementation."""
        self.mock_delegate.on_account_list_update(
            account_list=['DU0000140', 'DU0000141']
        )

        self.assertTrue(self.mock_delegate.accounts)

    @utils.async_test
    async def test_managed_accounts(self):
        """Test overridden function `managedAccounts`."""
        self.client.reqManagedAccts()

        await asyncio.sleep(1)

        self.assertTrue(self.mock_delegate.accounts)

    #region - account updates
    @utils.async_test
    async def test_update_account_value(self):
        """Test overridden function `updateAccountValue`."""
        await self._start_account_updates()
        await self._cancel_account_updates()

        result: list = await self.mock_delegate.account_updates_queue.get()
        self.assertTrue(
            any(isinstance(data, models.RawAccountValueData) for data in result)
        )

    @utils.async_test
    async def test_update_portfolio(self):
        """Test overridden function `updatePortfolio`."""
        await self._start_account_updates()
        await self._cancel_account_updates()

        result: list = await self.mock_delegate.account_updates_queue.get()
        self.assertTrue(
            any(isinstance(data, models.RawPortfolioData) for data in result)
        )

    @utils.async_test
    async def test_update_account_time(self):
        """Test overridden function `updateAccountTime`."""
        await self._start_account_updates()
        await self._cancel_account_updates()

        result: list = await self.mock_delegate.account_updates_queue.get()
        self.assertRegex(
            next(data for data in result if isinstance(data, str)),
            r"\d{2}:\d{2}"
        )
    #endregion - account updates

    @classmethod
    def tearDownClass(cls):
        cls.client.disconnect()

    #region - Private functions
    async def _start_account_updates(self):
        self.client.reqAccountUpdates(subscribe=True,
                                      acctCode=os.getenv("IB_ACC_ID", ""))
        await asyncio.sleep(1)

    async def _cancel_account_updates(self):
        self.client.reqAccountUpdates(subscribe=False,
                                      acctCode=os.getenv("IB_ACC_ID", ""))
        await asyncio.sleep(0.5)
        self.mock_delegate.account_updates_queue.put(fq._Status.FINISHED)
    #endregion
