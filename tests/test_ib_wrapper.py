"""
Unit tests for module `ibpy_native.wrapper`.
"""
import os
import enum
import threading
import unittest

from ibpy_native import client, wrapper
from ibpy_native.finishable_queue import FinishableQueue, Status
from ibapi.contract import Contract
from ibapi.wrapper import (
    HistoricalTick, HistoricalTickBidAsk, HistoricalTickLast,
    ListOfHistoricalTick, ListOfHistoricalTickBidAsk, ListOfHistoricalTickLast
)

class Const(enum.IntEnum):
    """
    Predefined constants for `TestIBWrapper`.
    """
    RID_RESOLVE_CONTRACT = 43
    RID_FETCH_HISTORICAL_TICKS = 18001
    RID_REQ_TICK_BY_TICK_DATA = 19001
    QUEUE_MAX_WAIT_SEC = 10

class TestIBWrapper(unittest.TestCase):
    """
    Unit tests for class `IBWrapper`.
    """
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

        cls.resolved_contract = cls.client.resolve_contract(
            Const.RID_RESOLVE_CONTRACT.value, cls.__contract
        )

        print(cls.resolved_contract)

    def test_historical_ticks(self):
        """
        Test overridden function `historicalTicks`.
        """
        end_time = "20200327 16:30:00"

        queue = self.wrapper.get_request_queue(
            Const.RID_FETCH_HISTORICAL_TICKS
        )

        f_queue = FinishableQueue(queue)

        self.client.reqHistoricalTicks(
            Const.RID_FETCH_HISTORICAL_TICKS.value, self.resolved_contract,
            "", end_time, 1000, "MIDPOINT", 1, False, []
        )

        result = f_queue.get(timeout=Const.QUEUE_MAX_WAIT_SEC)

        self.assertFalse(self.wrapper.has_err())
        self.assertNotEqual(f_queue.get_status(), Status.TIMEOUT)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], ListOfHistoricalTick)

    def test_historical_ticks_bid_ask(self):
        """
        Test overridden function `historicalTicksBidAsk`.
        """
        end_time = "20200327 16:30:00"

        queue = self.wrapper.get_request_queue(
            Const.RID_FETCH_HISTORICAL_TICKS
        )

        f_queue = FinishableQueue(queue)

        self.client.reqHistoricalTicks(
            Const.RID_FETCH_HISTORICAL_TICKS.value, self.resolved_contract,
            "", end_time, 1000, "BID_ASK", 1, False, []
        )

        result = f_queue.get(timeout=Const.QUEUE_MAX_WAIT_SEC)

        self.assertFalse(self.wrapper.has_err())
        self.assertNotEqual(f_queue.get_status(), Status.TIMEOUT)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], ListOfHistoricalTickBidAsk)

    def test_historical_ticks_last(self):
        """
        Test overridden function `historicalTicksLast`.
        """
        end_time = "20200327 16:30:00"

        queue = self.wrapper.get_request_queue(
            Const.RID_FETCH_HISTORICAL_TICKS
        )

        f_queue = FinishableQueue(queue)

        self.client.reqHistoricalTicks(
            Const.RID_FETCH_HISTORICAL_TICKS.value, self.resolved_contract,
            "", end_time, 1000, "TRADES", 1, False, []
        )

        result = f_queue.get(timeout=Const.QUEUE_MAX_WAIT_SEC)

        self.assertFalse(self.wrapper.has_err())
        self.assertNotEqual(f_queue.get_status(), Status.TIMEOUT)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], ListOfHistoricalTickLast)

    def test_tick_by_tick_all_last(self):
        """
        Test overridden function `tickByTickAllLast`.
        """
        f_queue = FinishableQueue(self.wrapper.get_request_queue(
            Const.RID_REQ_TICK_BY_TICK_DATA
        ))

        self.client.reqTickByTickData(
            reqId=Const.RID_REQ_TICK_BY_TICK_DATA.value,
            contract=self.resolved_contract,
            tickType='AllLast',
            numberOfTicks=0,
            ignoreSize=True
        )

        for tick in f_queue.stream():
            self.assertIsInstance(tick, HistoricalTickLast)
            break

        self.client.cancelTickByTickData(Const.RID_REQ_TICK_BY_TICK_DATA.value)

    def test_tick_by_tick_last(self):
        """
        Test overridden function `tickByTickAllLast` with tick type `Last`.
        """
        f_queue = FinishableQueue(self.wrapper.get_request_queue(
            Const.RID_REQ_TICK_BY_TICK_DATA
        ))

        self.client.reqTickByTickData(
            reqId=Const.RID_REQ_TICK_BY_TICK_DATA.value,
            contract=self.resolved_contract,
            tickType='Last',
            numberOfTicks=0,
            ignoreSize=True
        )

        for tick in f_queue.stream():
            self.assertIsInstance(tick, HistoricalTickLast)
            break

    def test_tick_by_tick_bid_ask(self):
        """
        Test overridden function `tickByTickBidAsk`.
        """
        f_queue = FinishableQueue(self.wrapper.get_request_queue(
            Const.RID_REQ_TICK_BY_TICK_DATA
        ))

        self.client.reqTickByTickData(
            reqId=Const.RID_REQ_TICK_BY_TICK_DATA.value,
            contract=self.resolved_contract,
            tickType='BidAsk',
            numberOfTicks=0,
            ignoreSize=True
        )

        for tick in f_queue.stream():
            self.assertIsInstance(tick, HistoricalTickBidAsk)
            break

        self.client.cancelTickByTickData(Const.RID_REQ_TICK_BY_TICK_DATA.value)

    def test_tick_by_tick_mid_point(self):
        """
        Test overridden function `tickByTickMidPoint`.
        """
        queue = self.wrapper.get_request_queue(
            Const.RID_REQ_TICK_BY_TICK_DATA
        )

        f_queue = FinishableQueue(queue)

        self.client.reqTickByTickData(
            reqId=Const.RID_REQ_TICK_BY_TICK_DATA.value,
            contract=self.resolved_contract,
            tickType='MidPoint',
            numberOfTicks=0,
            ignoreSize=True
        )

        for tick in f_queue.stream():
            self.assertIsInstance(tick, HistoricalTick)
            break

        self.client.cancelTickByTickData(Const.RID_REQ_TICK_BY_TICK_DATA)

    @classmethod
    def tearDownClass(cls):
        cls.client.disconnect()
