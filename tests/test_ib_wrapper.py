"""
Unit tests for module `ibpy_native.wrapper`.
"""
import enum
import threading
import unittest

from ibpy_native import client, wrapper
from ibpy_native.finishable_queue import FinishableQueue, Status
from ibapi.contract import Contract
from ibapi.wrapper import (
    ListOfHistoricalTick, ListOfHistoricalTickBidAsk, ListOfHistoricalTickLast
)

class Const(enum.Enum):
    """
    Predefined constants for `TestIBWrapper`.
    """
    RID_RESOLVE_CONTRACT = 43
    RID_FETCH_HISTORICAL_TICKS = 18001
    QUEUE_MAX_WAIT_SEC = 10

class TestIBWrapper(unittest.TestCase):
    """
    Unit tests for class `IBWrapper`.
    """
    __contract = Contract()
    __contract.secType = "STK"
    __contract.symbol = "AAPL"
    __contract.exchange = "SMART"
    __contract.currency = "USD"

    @classmethod
    def setUpClass(cls):
        cls.wrapper = wrapper.IBWrapper()
        cls.client = client.IBClient(cls.wrapper)

        cls.client.connect('127.0.0.1', 4002, 1001)

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
            Const.RID_FETCH_HISTORICAL_TICKS.value
        )

        f_queue = FinishableQueue(queue)

        self.client.reqHistoricalTicks(
            Const.RID_FETCH_HISTORICAL_TICKS.value, self.resolved_contract,
            "", end_time, 1000, "MIDPOINT", 1, False, []
        )

        result = f_queue.get(timeout=Const.QUEUE_MAX_WAIT_SEC.value)

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
            Const.RID_FETCH_HISTORICAL_TICKS.value
        )

        f_queue = FinishableQueue(queue)

        self.client.reqHistoricalTicks(
            Const.RID_FETCH_HISTORICAL_TICKS.value, self.resolved_contract,
            "", end_time, 1000, "BID_ASK", 1, False, []
        )

        result = f_queue.get(timeout=Const.QUEUE_MAX_WAIT_SEC.value)

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
            Const.RID_FETCH_HISTORICAL_TICKS.value
        )

        f_queue = FinishableQueue(queue)

        self.client.reqHistoricalTicks(
            Const.RID_FETCH_HISTORICAL_TICKS.value, self.resolved_contract,
            "", end_time, 1000, "TRADES", 1, False, []
        )

        result = f_queue.get(timeout=Const.QUEUE_MAX_WAIT_SEC.value)

        self.assertFalse(self.wrapper.has_err())
        self.assertNotEqual(f_queue.get_status(), Status.TIMEOUT)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], ListOfHistoricalTickLast)

    @classmethod
    def tearDownClass(cls):
        cls.client.disconnect()
