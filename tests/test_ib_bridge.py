from source.ib import IBBridge

import unittest

class TestIBBridge(unittest.TestCase):
    
    def test_init_auto_connect(self):
        bridge = IBBridge(port=4002, client_id=1001)
        
        self.assertTrue(bridge.is_connected)
        
        bridge.disconnect()
