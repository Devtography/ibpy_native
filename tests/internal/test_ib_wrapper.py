"""Unit tests for module `ibpy_native.wrapper`."""
import asyncio
import os
import enum
import threading
import unittest

from ibapi import contract as ib_contract
from ibapi import wrapper as ib_wrapper

from ibpy_native.interfaces import listeners
from ibpy_native.internal import client as ibpy_client
from ibpy_native.internal import wrapper as ibpy_wrapper
from ibpy_native.utils import finishable_queue as fq

from tests import utils

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
    """Unit tests for class `IBWrapper`."""
    __contract = ib_contract.Contract()
    # __contract.secType = 'STK'
    # __contract.symbol = 'AAPL'
    # __contract.exchange = 'SMART'
    __contract.secType = 'FUT'
    __contract.symbol = 'YM'
    __contract.lastTradeDateOrContractMonth = '202009'
    __contract.currency = "USD"

    @classmethod
    def setUpClass(cls):
        cls.wrapper = ibpy_wrapper.IBWrapper()
        cls.client = ibpy_client.IBClient(cls.wrapper)

        cls.client.connect(
            os.getenv('IB_HOST', '127.0.0.1'),
            int(os.getenv('IB_PORT', '4002')),
            1001
        )

        thread = threading.Thread(target=cls.client.run)
        thread.start()

        setattr(cls.client, "_thread", thread)

        cls.resolved_contract = asyncio.run(
            cls.client.resolve_contract(
                Const.RID_RESOLVE_CONTRACT.value, cls.__contract
            )
        )

        print(cls.resolved_contract)

    @utils.async_test
    async def test_next_req_id(self):
        # pylint: disable=protected-access
        """Test retrieval of next usable request ID."""
        # Prepare the `FinishableQueue` objects in internal `__req_queue`
        self.wrapper._IBWrapper__req_queue.clear()
        _ = self.wrapper.get_request_queue(req_id=0)
        f_queue = self.wrapper.get_request_queue(req_id=1)
        _ = self.wrapper.get_request_queue(req_id=10)

        self.assertEqual(self.wrapper.next_req_id, 11)

        f_queue.put(fq.Status.FINISHED)
        await f_queue.get()
        self.assertEqual(self.wrapper.next_req_id, 1)

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

        self.wrapper.set_on_notify_listener(listener=mock_listener)
        self.wrapper.error(reqId=-1, errorCode=1100, errorString="MOCK MSG")

        self.assertTrue(mock_listener.triggered)

    @utils.async_test
    async def test_historical_ticks(self):
        """Test overridden function `historicalTicks`."""
        end_time = "20200327 16:30:00"

        f_queue = self.wrapper.get_request_queue(
            Const.RID_FETCH_HISTORICAL_TICKS
        )

        self.client.reqHistoricalTicks(
            Const.RID_FETCH_HISTORICAL_TICKS.value, self.resolved_contract,
            "", end_time, 1000, "MIDPOINT", 1, False, []
        )

        result = await f_queue.get()

        self.assertEqual(f_queue.status, fq.Status.FINISHED)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], ib_wrapper.ListOfHistoricalTick)

    @utils.async_test
    async def test_historical_ticks_bid_ask(self):
        """Test overridden function `historicalTicksBidAsk`."""
        end_time = "20200327 16:30:00"

        f_queue = self.wrapper.get_request_queue(
            Const.RID_FETCH_HISTORICAL_TICKS
        )

        self.client.reqHistoricalTicks(
            Const.RID_FETCH_HISTORICAL_TICKS.value, self.resolved_contract,
            "", end_time, 1000, "BID_ASK", 1, False, []
        )

        result = await f_queue.get()

        self.assertEqual(f_queue.status, fq.Status.FINISHED)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], ib_wrapper.ListOfHistoricalTickBidAsk)

    @utils.async_test
    async def test_historical_ticks_last(self):
        """Test overridden function `historicalTicksLast`."""
        end_time = "20200327 16:30:00"

        f_queue = self.wrapper.get_request_queue(
            Const.RID_FETCH_HISTORICAL_TICKS
        )

        self.client.reqHistoricalTicks(
            Const.RID_FETCH_HISTORICAL_TICKS.value, self.resolved_contract,
            "", end_time, 1000, "TRADES", 1, False, []
        )

        result = await f_queue.get()

        self.assertEqual(f_queue.status, fq.Status.FINISHED)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], ib_wrapper.ListOfHistoricalTickLast)

    @utils.async_test
    async def test_tick_by_tick_all_last(self):
        """Test overridden function `tickByTickAllLast`."""
        f_queue = self.wrapper.get_request_queue(
            Const.RID_REQ_TICK_BY_TICK_DATA_ALL_LAST
        )

        self.client.reqTickByTickData(
            reqId=Const.RID_REQ_TICK_BY_TICK_DATA_ALL_LAST.value,
            contract=self.resolved_contract,
            tickType='AllLast',
            numberOfTicks=0,
            ignoreSize=True
        )

        async for ele in f_queue.stream():
            self.assertIsInstance(ele,
                                  (ib_wrapper.HistoricalTickLast, fq.Status))
            self.assertIsNot(ele, fq.Status.ERROR)

            if ele is not fq.Status.FINISHED:
                self.client.cancelTickByTickData(
                    Const.RID_REQ_TICK_BY_TICK_DATA_ALL_LAST.value
                )

                f_queue.put(fq.Status.FINISHED)

    @utils.async_test
    async def test_tick_by_tick_last(self):
        """Test overridden function `tickByTickAllLast` with tick type `Last`.
        """
        f_queue = self.wrapper.get_request_queue(
            Const.RID_REQ_TICK_BY_TICK_DATA_LAST
        )

        self.client.reqTickByTickData(
            reqId=Const.RID_REQ_TICK_BY_TICK_DATA_LAST.value,
            contract=self.resolved_contract,
            tickType='Last',
            numberOfTicks=0,
            ignoreSize=True
        )

        async for ele in f_queue.stream():
            self.assertIsInstance(ele,
                                  (ib_wrapper.HistoricalTickLast, fq.Status))
            self.assertIsNot(ele, fq.Status.ERROR)

            if ele is not fq.Status.FINISHED:
                self.client.cancelTickByTickData(
                    Const.RID_REQ_TICK_BY_TICK_DATA_LAST.value
                )

                f_queue.put(fq.Status.FINISHED)


    @utils.async_test
    async def test_tick_by_tick_bid_ask(self):
        """Test overridden function `tickByTickBidAsk`."""
        f_queue = self.wrapper.get_request_queue(
            Const.RID_REQ_TICK_BY_TICK_DATA_BIDASK
        )

        self.client.reqTickByTickData(
            reqId=Const.RID_REQ_TICK_BY_TICK_DATA_BIDASK.value,
            contract=self.resolved_contract,
            tickType='BidAsk',
            numberOfTicks=0,
            ignoreSize=True
        )

        async for ele in f_queue.stream():
            self.assertIsInstance(ele,
                                  (ib_wrapper.HistoricalTickBidAsk, fq.Status))
            self.assertIsNot(ele, fq.Status.ERROR)

            if ele is not fq.Status.FINISHED:
                self.client.cancelTickByTickData(
                    Const.RID_REQ_TICK_BY_TICK_DATA_BIDASK.value
                )

                f_queue.put(fq.Status.FINISHED)

    @utils.async_test
    async def test_tick_by_tick_mid_point(self):
        """Test overridden function `tickByTickMidPoint`."""
        f_queue = self.wrapper.get_request_queue(
            Const.RID_REQ_TICK_BY_TICK_DATA_MIDPOINT
        )

        self.client.reqTickByTickData(
            reqId=Const.RID_REQ_TICK_BY_TICK_DATA_MIDPOINT.value,
            contract=self.resolved_contract,
            tickType='MidPoint',
            numberOfTicks=0,
            ignoreSize=True
        )

        async for ele in f_queue.stream():
            self.assertIsInstance(ele,
                                  (ib_wrapper.HistoricalTick, fq.Status))
            self.assertIsNot(ele, fq.Status.ERROR)

            if ele is not fq.Status.FINISHED:
                self.client.cancelTickByTickData(
                    Const.RID_REQ_TICK_BY_TICK_DATA_MIDPOINT.value
                )

                f_queue.put(fq.Status.FINISHED)

    @classmethod
    def tearDownClass(cls):
        cls.client.disconnect()
