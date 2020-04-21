from source.ib import wrapper
from source.ib import client
from ibapi.contract import Contract

import unittest
import threading

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

        resolved_contract = self.client.resolve_contract(contract, 43)

        self.assertIsNotNone(resolved_contract)
        print(resolved_contract)

    def tearDown(self):
        self.client.disconnect()
