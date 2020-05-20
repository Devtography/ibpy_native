from ibpy_native.wrapper import IBWrapper 
from ibpy_native.client import IBClient
from ibpy_native.error import IBError

from ibapi.contract import Contract
from ibapi.wrapper import (HistoricalTick, HistoricalTickBidAsk,
    HistoricalTickLast)
from datetime import datetime
from typing import List

import enum
import unittest
import threading
import pytz

class Const(enum.IntEnum):
    RID_RESOLVE_CONTRACT = 43
    RID_RESOLVE_HEAD_TIMESTAMP = 14001
    RID_RESOLVE_HEAD_TIMESTAMP_EPOCH = 14002
    RID_FETCH_HISTORICAL_TICKS = 18001
    RID_FETCH_HISTORICAL_TICKS_ERR = 18002

class TestIBClient(unittest.TestCase):
    __contract = Contract()
    __contract.secType = "STK"
    __contract.symbol = "AAPL"
    __contract.exchange = "SMART"
    __contract.currency = "USD"

    @classmethod
    def setUpClass(self):
        IBClient.TZ = pytz.timezone('America/New_York')

        self.wrapper = IBWrapper()
        self.client = IBClient(self.wrapper)

        self.client.connect('127.0.0.1', 4002, 1001)

        thread = threading.Thread(target = self.client.run)
        thread.start()

        setattr(self.client, "_thread", thread)

    def test_resolve_contract(self):
        contract = Contract()
        contract.secType = "FUT"
        contract.lastTradeDateOrContractMonth = "202006"
        contract.symbol = "MYM"
        contract.exchange = "ECBOT"

        resolved_contract = self.client.resolve_contract(
            Const.RID_RESOLVE_CONTRACT.value, contract
        )

        self.assertIsNotNone(resolved_contract)
        print(resolved_contract)

    def test_resolve_head_timestamp(self):
        resolved_contract = self.client.resolve_contract(
            Const.RID_RESOLVE_CONTRACT.value, self.__contract
        )

        print(resolved_contract)

        head_timestamp = self.client.resolve_head_timestamp(
            Const.RID_RESOLVE_HEAD_TIMESTAMP.value, resolved_contract
        )

        print(head_timestamp)

        self.assertIsNotNone(head_timestamp)
        self.assertIsInstance(head_timestamp, int)

    def test_fetch_historical_ticks(self):
        timeout = 60

        resolved_contract = self.client.resolve_contract(
            Const.RID_RESOLVE_CONTRACT.value, self.__contract
        )

        data = self.client.fetch_historical_ticks(
            Const.RID_FETCH_HISTORICAL_TICKS.value, resolved_contract, 
            start=IBClient.TZ.localize(
                datetime(2020, 4, 29, 10, 30, 0)
            ),
            end=IBClient.TZ.localize(
                datetime(2020, 4, 29, 10, 31, 0)
            ),
            show='MIDPOINT', timeout=timeout
        )

        self.assertIsInstance(data[0], list)
        self.assertTrue(data[1], True)
        self.assertGreater(len(data[0]), 0)
        self.assertIsInstance(data[0][0], HistoricalTick)

        data = self.client.fetch_historical_ticks(
            Const.RID_FETCH_HISTORICAL_TICKS.value, resolved_contract, 
            start=IBClient.TZ.localize(
                datetime(2020, 4, 29, 10, 30, 0)
            ),
            end=IBClient.TZ.localize(
                datetime(2020, 4, 29, 10, 31, 0)
            ),
            show='BID_ASK', timeout=timeout
        )

        self.assertIsInstance(data[0], list)
        self.assertTrue(data[1], True)
        self.assertGreater(len(data[0]), 0)
        self.assertIsInstance(data[0][0], HistoricalTickBidAsk)

        data = self.client.fetch_historical_ticks(
            Const.RID_FETCH_HISTORICAL_TICKS.value, resolved_contract, 
            start=IBClient.TZ.localize(
                datetime(2020, 4, 29, 10, 30, 0)
            ),
            end=IBClient.TZ.localize(
                datetime(2020, 4, 29, 10, 31, 0)
            ),
            timeout=timeout
        )

        self.assertIsInstance(data[0], list)
        self.assertTrue(data[1], True)
        self.assertGreater(len(data[0]), 0)
        self.assertIsInstance(data[0][0], HistoricalTickLast)

    def test_fetch_historical_ticks_err(self):
        resolved_contract = self.client.resolve_contract(
            Const.RID_RESOLVE_CONTRACT.value, self.__contract
        )

        # Incorrect value of `show`
        with self.assertRaises(ValueError):
            self.client.fetch_historical_ticks(
                Const.RID_FETCH_HISTORICAL_TICKS_ERR.value, resolved_contract,
                datetime.now(), show='LAST'
            )

        # Timezone of start & end are not identical
        with self.assertRaises(ValueError):
            self.client.fetch_historical_ticks(
                Const.RID_FETCH_HISTORICAL_TICKS_ERR.value, resolved_contract,
                datetime.now().astimezone(pytz.timezone('Asia/Hong_Kong')),
                datetime.now().astimezone(pytz.timezone('America/New_York'))
            )

        # Invalid contract object
        with self.assertRaises(IBError):
            self.client.fetch_historical_ticks(
                Const.RID_FETCH_HISTORICAL_TICKS_ERR.value, Contract(),
                datetime(2020, 5, 20, 3, 20, 0).astimezone(IBClient.TZ),
                datetime.now().astimezone(IBClient.TZ)
            )

    @classmethod
    def tearDownClass(self):
        self.client.disconnect()
