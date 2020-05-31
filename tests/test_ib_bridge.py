"""
Unit tests for module `ibpy_native.bridge`.
"""
import unittest
from datetime import datetime

import pytz
from ibpy_native import IBBridge
from ibpy_native.client import IBClient
from ibapi.wrapper import Contract

TEST_PORT = 4002
TEST_ID = 1001

class TestIBBridgeConn(unittest.TestCase):
    """
    Test cases for connection related functions in `IBBridge`
    """

    def test_init_auto_connect(self):
        """
        Test initialise `IBBridge` with `auto_conn=True`.
        """
        bridge = IBBridge(port=TEST_PORT, client_id=TEST_ID)

        self.assertTrue(bridge.is_connected())

        bridge.disconnect()

    def test_init_manual_connect(self):
        """
        Test initialise `IBBridge` with `auto_conn=False`.
        """
        bridge = IBBridge(port=TEST_PORT, client_id=TEST_ID, auto_conn=False)
        bridge.connect()

        self.assertTrue(bridge.is_connected())

        bridge.disconnect()

    def test_disconnect_without_connection(self):
        """
        Test function `disconnect` without an established connection.
        """
        bridge = IBBridge(port=TEST_PORT, client_id=TEST_ID, auto_conn=False)
        bridge.disconnect()

        self.assertFalse(bridge.is_connected())

class TestIBBridge(unittest.TestCase):
    """
    Unit tests for class `IBBridge`.
    """

    @classmethod
    def setUpClass(cls):
        cls._bridge = IBBridge(port=TEST_PORT, client_id=TEST_ID)

    def test_set_timezone(self):
        """
        Test function `set_timezone`.
        """
        IBBridge.set_timezone(pytz.timezone('Asia/Hong_Kong'))

        self.assertEqual(IBClient.TZ, pytz.timezone('Asia/Hong_Kong'))

        # Reset timezone to New York
        IBBridge.set_timezone(pytz.timezone('America/New_York'))
        self.assertEqual(IBClient.TZ, pytz.timezone('America/New_York'))

    def test_get_us_stock_contract(self):
        """
        Test function `get_us_stock_contract`.
        """
        contract = self._bridge.get_us_stock_contract('AAPL')

        self.assertIsInstance(contract, Contract)

    def test_get_us_future_contract(self):
        """
        Test function `get_us_future_contract`.
        """
        contract = self._bridge.get_us_future_contract('MYM')
        self.assertIsInstance(contract, Contract)

        with self.assertRaises(ValueError):
            self._bridge.get_us_future_contract('MYM', 'abcd')

    def test_get_earliest_data_point(self):
        """
        Test function `get_earliest_data_point`.
        """
        contract = self._bridge.get_us_stock_contract('AAPL')

        head_trade = self._bridge.get_earliest_data_point(contract)
        self.assertEqual(datetime(1980, 12, 12, 9, 30), head_trade)

        head_bid_ask = self._bridge.get_earliest_data_point(contract, 'BID_ASK')
        self.assertEqual(datetime(2004, 1, 23, 9, 30), head_bid_ask)

    def test_get_historical_ticks(self):
        """
        Test function `get_historical_ticks`.
        """
        contract = self._bridge.get_us_future_contract('mym', '202003')

        result = self._bridge.get_historical_ticks(
            contract,
            datetime(2020, 3, 16, 6, 30),
            datetime(2020, 3, 16, 11, 0, 0),
            timeout=120
        )

        self.assertGreater(len(result['ticks']), 0)
        self.assertTrue(result['completed'])

    def test_get_historical_ticks_err(self):
        """
        Test function `get_historical_ticks` for the error cases.
        """
        contract = self._bridge.get_us_stock_contract('AAPL')

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
