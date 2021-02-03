"""Unit test for module `ibpy_native.models.account`."""
import unittest

from ibpy_native.models import account

class TestAccountModel(unittest.TestCase):
    """Unit test for model class `Account`"""

    def setUp(self):
        self.account = account.Account(account_id="DU0000140")

    def test_get_set_account_value(self):
        """Test the implementation of account value's getter & setter."""
        self.account.update_account_value(key="AccountReady",
                                          currency="",
                                          val="true")
        self.account.update_account_value(key="AvailableFunds",
                                          currency="BASE",
                                          val="25000")
        self.assertEqual("true",
                         self.account.get_account_value(key="AccountReady"))
        self.assertEqual("25000",
                         self.account.get_account_value(key="AvailableFunds",
                                                        currency="BASE"))
        self.assertIsNone(self.account.get_account_value(key="AvailableFunds",
                                                         currency="USD"))
        self.assertIsNone(self.account.get_account_value(key="AccountCode"))
        