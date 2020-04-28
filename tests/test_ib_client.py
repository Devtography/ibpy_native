from source.ib import wrapper
from source.ib import client
from ibapi.contract import Contract

import enum
import unittest
import threading

class Const(enum.Enum):
    RID_RESOLVE_CONTRACT = 43
    RID_RESOLVE_HEAD_TIMESTAMP = 14001
    RID_RESOLVE_HEAD_TIMESTAMP_EPOCH = 14002

class TestIBClient(unittest.TestCase):

    def setUp(self):
        self.wrapper = wrapper.IBWrapper()
        self.client = client.IBClient(self.wrapper)

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
            contract, Const.RID_RESOLVE_CONTRACT.value
        )

        self.assertIsNotNone(resolved_contract)
        print(resolved_contract)

    def test_resolve_head_timestamp(self):
        contract = Contract()
        contract.secType = "STK"
        contract.symbol = "AAPL"
        contract.exchange = "SMART"
        contract.currency = "USD"

        resolved_contract = self.client.resolve_contract(
            contract, Const.RID_RESOLVE_CONTRACT.value
        )

        print(resolved_contract)

        head_timestamp = self.client.resolve_head_timestamp(
            resolved_contract, Const.RID_RESOLVE_HEAD_TIMESTAMP.value
        )

        print(head_timestamp)

        self.assertIsNotNone(head_timestamp)
        self.assertIsInstance(head_timestamp, str)

        head_timestamp = self.client.resolve_head_timestamp(
            contract, Const.RID_RESOLVE_HEAD_TIMESTAMP_EPOCH.value, True
        )

        print(head_timestamp)

        self.assertIsNotNone(head_timestamp)
        self.assertTrue(head_timestamp.isdecimal())

    def tearDown(self):
        self.client.disconnect()
