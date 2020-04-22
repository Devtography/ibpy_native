from source.ib import IBBridge

import unittest

TEST_PORT = 4002
TEST_ID = 1001

class TestIBBridge(unittest.TestCase):
    
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
