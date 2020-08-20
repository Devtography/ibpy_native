"""Unit tests for module `ibpy_native.wrapper`."""
import asyncio
import os
import enum
import threading
import unittest

from ibpy_native.interfaces.listeners import NotificationListener
from ibpy_native.internal import client, wrapper
from ibpy_native.utils import finishable_queue as fq
from ibapi.contract import Contract
from ibapi.wrapper import (
    HistoricalTick, HistoricalTickBidAsk, HistoricalTickLast,
    ListOfHistoricalTick, ListOfHistoricalTickBidAsk, ListOfHistoricalTickLast
)
from tests.utils import async_test

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
    __contract = Contract()
    # __contract.secType = 'STK'
    # __contract.symbol = 'AAPL'
    # __contract.exchange = 'SMART'
    __contract.secType = 'FUT'
    __contract.symbol = 'YM'
    __contract.lastTradeDateOrContractMonth = '202009'
    __contract.currency = "USD"

    @classmethod
    def setUpClass(cls):
        cls.wrapper = wrapper.IBWrapper()
        cls.client = client.IBClient(cls.wrapper)

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

    def test_notification_listener(self):
        """Test notification listener approach."""
        class MockListener(NotificationListener):
            """Mock notification listener
            """
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

    @async_test
    async def test_historical_ticks(self):
        """
        Test overridden function `historicalTicks`.
        """
        end_time = "20200327 16:30:00"

        queue = self.wrapper.get_request_queue(
            Const.RID_FETCH_HISTORICAL_TICKS
        )

        f_queue = fq.FinishableQueue(queue)

        self.client.reqHistoricalTicks(
            Const.RID_FETCH_HISTORICAL_TICKS.value, self.resolved_contract,
            "", end_time, 1000, "MIDPOINT", 1, False, []
        )

        result = await f_queue.get()

        self.assertFalse(self.wrapper.has_err())
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], ListOfHistoricalTick)

    @async_test
    async def test_historical_ticks_bid_ask(self):
        """Test overridden function `historicalTicksBidAsk`."""
        end_time = "20200327 16:30:00"

        queue = self.wrapper.get_request_queue(
            Const.RID_FETCH_HISTORICAL_TICKS
        )

        f_queue = fq.FinishableQueue(queue)

        self.client.reqHistoricalTicks(
            Const.RID_FETCH_HISTORICAL_TICKS.value, self.resolved_contract,
            "", end_time, 1000, "BID_ASK", 1, False, []
        )

        result = await f_queue.get()

        self.assertFalse(self.wrapper.has_err())
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], ListOfHistoricalTickBidAsk)

    @async_test
    async def test_historical_ticks_last(self):
        """Test overridden function `historicalTicksLast`."""
        end_time = "20200327 16:30:00"

        queue = self.wrapper.get_request_queue(
            Const.RID_FETCH_HISTORICAL_TICKS
        )

        f_queue = fq.FinishableQueue(queue)

        self.client.reqHistoricalTicks(
            Const.RID_FETCH_HISTORICAL_TICKS.value, self.resolved_contract,
            "", end_time, 1000, "TRADES", 1, False, []
        )

        result = await f_queue.get()

        self.assertFalse(self.wrapper.has_err())
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], ListOfHistoricalTickLast)

    @async_test
    async def test_tick_by_tick_all_last(self):
        """Test overridden function `tickByTickAllLast`."""
        queue = self.wrapper.get_request_queue(
            Const.RID_REQ_TICK_BY_TICK_DATA_ALL_LAST
        )

        f_queue = fq.FinishableQueue(queue)

        self.client.reqTickByTickData(
            reqId=Const.RID_REQ_TICK_BY_TICK_DATA_ALL_LAST.value,
            contract=self.resolved_contract,
            tickType='AllLast',
            numberOfTicks=0,
            ignoreSize=True
        )

        async for ele in f_queue.stream():
            self.assertIsInstance(ele, (HistoricalTickLast, fq.Status))
            self.assertIsNot(ele, fq.Status.ERROR)

            if ele is not fq.Status.FINISHED:
                self.client.cancelTickByTickData(
                    Const.RID_REQ_TICK_BY_TICK_DATA_ALL_LAST.value
                )

                queue.put(fq.Status.FINISHED)

    @async_test
    async def test_tick_by_tick_last(self):
        """Test overridden function `tickByTickAllLast` with tick type `Last`.
        """
        queue = self.wrapper.get_request_queue(
            Const.RID_REQ_TICK_BY_TICK_DATA_LAST
        )

        f_queue = fq.FinishableQueue(queue)

        self.client.reqTickByTickData(
            reqId=Const.RID_REQ_TICK_BY_TICK_DATA_LAST.value,
            contract=self.resolved_contract,
            tickType='Last',
            numberOfTicks=0,
            ignoreSize=True
        )

        async for ele in f_queue.stream():
            self.assertIsInstance(ele, (HistoricalTickLast, fq.Status))
            self.assertIsNot(ele, fq.Status.ERROR)

            if ele is not fq.Status.FINISHED:
                self.client.cancelTickByTickData(
                    Const.RID_REQ_TICK_BY_TICK_DATA_LAST.value
                )

                queue.put(fq.Status.FINISHED)


    @async_test
    async def test_tick_by_tick_bid_ask(self):
        """Test overridden function `tickByTickBidAsk`."""
        queue = self.wrapper.get_request_queue(
            Const.RID_REQ_TICK_BY_TICK_DATA_BIDASK
        )

        f_queue = fq.FinishableQueue(queue)

        self.client.reqTickByTickData(
            reqId=Const.RID_REQ_TICK_BY_TICK_DATA_BIDASK.value,
            contract=self.resolved_contract,
            tickType='BidAsk',
            numberOfTicks=0,
            ignoreSize=True
        )

        async for ele in f_queue.stream():
            self.assertIsInstance(ele, (HistoricalTickBidAsk, fq.Status))
            self.assertIsNot(ele, fq.Status.ERROR)

            if ele is not fq.Status.FINISHED:
                self.client.cancelTickByTickData(
                    Const.RID_REQ_TICK_BY_TICK_DATA_BIDASK.value
                )

                queue.put(fq.Status.FINISHED)

    @async_test
    async def test_tick_by_tick_mid_point(self):
        """Test overridden function `tickByTickMidPoint`."""
        queue = self.wrapper.get_request_queue(
            Const.RID_REQ_TICK_BY_TICK_DATA_MIDPOINT
        )

        f_queue = fq.FinishableQueue(queue)

        self.client.reqTickByTickData(
            reqId=Const.RID_REQ_TICK_BY_TICK_DATA_MIDPOINT.value,
            contract=self.resolved_contract,
            tickType='MidPoint',
            numberOfTicks=0,
            ignoreSize=True
        )

        async for ele in f_queue.stream():
            self.assertIsInstance(ele, (HistoricalTick, fq.Status))
            self.assertIsNot(ele, fq.Status.ERROR)

            if ele is not fq.Status.FINISHED:
                self.client.cancelTickByTickData(
                    Const.RID_REQ_TICK_BY_TICK_DATA_MIDPOINT
                )

                queue.put(fq.Status.FINISHED)

    @classmethod
    def tearDownClass(cls):
        cls.client.disconnect()
