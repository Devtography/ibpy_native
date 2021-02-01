"""Unit tests for module `ibpy_native.account`."""
# pylint: disable=protected-access
import asyncio
import datetime
import unittest

from ibapi import contract as ib_contract
from ibpy_native import account
from ibpy_native import models
from ibpy_native.internal import client as ib_client
from ibpy_native.utils import finishable_queue as fq

from tests.toolkit import utils

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

    @utils.async_test
    async def test_sub_account_updates(self):
        """Test the implementation of `sub_account_updates`."""
        self._manager.on_account_list_update(account_list=[_MOCK_AC_140])

        updates_receiver = asyncio.create_task(
            self._manager.sub_account_updates(account_id=_MOCK_AC_140)
        )
        asyncio.create_task(self._simulate_account_updates(
            account_id=_MOCK_AC_140))

        await updates_receiver

        # Assert account value
        self.assertEqual(
            "25000",
            self._manager.accounts[0].get_account_value(key="AvailableFunds",
                currency="BASE")
        )
        self.assertEqual(datetime.time(hour=10, minute=10,
                                       tzinfo=ib_client._IBClient.TZ),
                         self._manager.accounts[0].last_update_time)

        # Assert portfolio data
        self.assertEqual(8, self._manager.accounts[0].positions[0].avg_cost)
        self.assertEqual(datetime.time(hour=10, minute=7,
                                       tzinfo=ib_client._IBClient.TZ),
                        self._manager.accounts[0].positions[0].last_update_time)
        self.assertEqual(20689,
                         (self._manager.accounts[0].positions[412888950]
                          .market_price))
        self.assertEqual(datetime.time(hour=10, minute=11,
                                       tzinfo=ib_client._IBClient.TZ),
                        (self._manager.accounts[0].positions[412888950]
                         .last_update_time))

    #region - Private functions
    async def _simulate_account_updates(self, account_id: str):
        self._manager.account_updates_queue.put(
           models.RawAccountValueData(account=account_id,
                                      currency="BASE",
                                      key="AvailableFunds",
                                      val="25000")
        )
        self._manager.account_updates_queue.put(
            models.RawPortfolioData(account=account_id,
                                    contract=ib_contract.Contract(),
                                    position=1,
                                    market_price=10.5,
                                    market_val=10.5,
                                    avg_cost=8,
                                    unrealised_pnl=2.5,
                                    realised_pnl=0)
        )
        self._manager.account_updates_queue.put("10:07")
        self._manager.account_updates_queue.put("10:10")

        second_contract = ib_contract.Contract()
        second_contract.conId = 412888950
        self._manager.account_updates_queue.put(
            models.RawPortfolioData(account=account_id,
                                    contract=second_contract,
                                    position=1,
                                    market_price=20689,
                                    market_val=20689,
                                    avg_cost=20600,
                                    unrealised_pnl=89,
                                    realised_pnl=0)
        )
        self._manager.account_updates_queue.put("10:11")

        self._manager.account_updates_queue.put(fq._Status.FINISHED)
    #endregion - Private functions
