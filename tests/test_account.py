"""Unit tests for module `ibpy_native.account`."""
import unittest

from ibpy_native import account
from ibpy_native import models

_MOCK_AC_140: str = 'DU0000140'
_MOCK_AC_141: str = 'DU0000141'
_MOCK_AC_142: str = 'DU0000142'
_MOCK_AC_143: str = 'DU0000143'

class TestAccountsManager(unittest.TestCase):
    """Unit tests for class `AccountsManager`."""

    def setUp(self):
        self._manager = account.AccountsManager()

    def test_on_account_list_update(self):
        """Test the implementation of function `on_account_list_update`."""
        self._manager.on_account_list_update(
            account_list=[_MOCK_AC_140, _MOCK_AC_141]
        )

        self.assertEqual(len(self._manager.accounts), 2)
        self.assertEqual(self._manager.accounts[0].account_id, _MOCK_AC_140)
        self.assertEqual(self._manager.accounts[1].account_id, _MOCK_AC_141)

    def test_on_account_list_update_existing_list(self):
        """Test the implementation of function `on_account_list_update` with an
        non empty account list in the `AccountsManager` instance.
        """
        # Prepends data into account list for test.
        self._manager = account.AccountsManager(
            accounts=[models.Account(account_id=_MOCK_AC_140),
                      models.Account(account_id=_MOCK_AC_142),
                      models.Account(account_id=_MOCK_AC_143)]
        )

        self._manager.on_account_list_update(
            account_list=[_MOCK_AC_140, _MOCK_AC_141]
        )

        self.assertEqual(len(self._manager.accounts), 2)
        self.assertEqual(self._manager.accounts[0].account_id, _MOCK_AC_140)
        self.assertEqual(self._manager.accounts[1].account_id, _MOCK_AC_141)
