from source.ib import IBBridge
from source.ib.client import IBClient

from ibapi.wrapper import Contract

import pytz
import unittest

TEST_PORT = 4002
TEST_ID = 1001

_RID_GET_US_STK = 43001

class TestIBBridgeConn(unittest.TestCase):
    """
    Test case for connection related functions in `IBBridge`
    """

    def test_init_auto_connect(self):
        bridge = IBBridge(port=TEST_PORT, client_id=TEST_ID)
        
        self.assertTrue(bridge.is_connected())
        
        bridge.disconnect()

    def test_init_manual_connect(self):
        bridge = IBBridge(port=TEST_PORT, client_id=TEST_ID, auto_conn=False)
        bridge.connect()

        self.assertTrue(bridge.is_connected())

        bridge.disconnect()

    def test_disconnect_without_connection(self):
        bridge = IBBridge(port=TEST_PORT, client_id=TEST_ID, auto_conn=False)
        bridge.disconnect()

        self.assertFalse(bridge.is_connected())

class TestIBBridge(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._bridge = IBBridge(port=TEST_PORT, client_id=TEST_ID)

    def test_set_timezone(self):
        IBBridge.set_timezone(pytz.timezone('Asia/Hong_Kong'))

        self.assertEqual(IBClient.TZ, pytz.timezone('Asia/Hong_Kong'))

        # Reset timezone to New York
        IBBridge.set_timezone(pytz.timezone('America/New_York'))
        self.assertEqual(IBClient.TZ, pytz.timezone('America/New_York'))

    def test_get_us_stock_contract(self):
        contract = self._bridge.get_us_stock_contract(_RID_GET_US_STK, 'AAPL')

        self.assertIsInstance(contract, Contract)

    @classmethod
    def tearDownClass(cls):
        cls._bridge.disconnect()
