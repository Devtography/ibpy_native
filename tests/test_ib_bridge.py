from source.ib import IBBridge
from source.ib.client import IBClient

from datetime import datetime
from ibapi.wrapper import Contract

import pytz
import unittest

TEST_PORT = 4002
TEST_ID = 1001

_RID_GET_US_STK = 43001
_RID_GET_HISTORICAL_TICKS = 18001
_RID_GET_HISTORICAL_TICKS_ERR = 18002

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

    def test_get_historical_ticks(self):
        contract = self._bridge.get_us_stock_contract(
            _RID_GET_HISTORICAL_TICKS, 'AAPL'
        )

        result = self._bridge.get_historical_ticks(
            contract,
            datetime(2020, 4, 29, 10, 30),
            datetime(2020, 4, 29, 10, 32)
        )

        self.assertGreater(len(result['ticks']), 0)
        self.assertTrue(result['completed'])

    def test_get_historical_ticks_err(self):
        contract = self._bridge.get_us_stock_contract(
            _RID_GET_HISTORICAL_TICKS_ERR, 'AAPL'
        )

        # start/end should not contains timezone info
        with self.assertRaises(ValueError):
            self._bridge.get_historical_ticks(
                contract, end=pytz.timezone('Asia/Hong_Kong').localize(
                    datetime(2020, 4, 28)
                )
            )

        # Invalid `data_type`
        with self.assertRaises(ValueError):
            self._bridge.get_historical_ticks(
                contract,
                data_type='BID'
            )

        # `start` is earlier than earliest available data point
        with self.assertRaises(ValueError):
            self._bridge.get_historical_ticks(contract, datetime(1972, 12, 12))

        with self.assertRaises(ValueError):
            self._bridge.get_historical_ticks(
                contract,
                datetime(2020, 4, 29, 9, 30),
                datetime(2020, 4, 28, 9, 30)
            )

    @classmethod
    def tearDownClass(cls):
        cls._bridge.disconnect()
