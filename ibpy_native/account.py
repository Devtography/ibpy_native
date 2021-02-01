"""IB account related resources."""
# pylint: disable=protected-access
import asyncio
import datetime
import re
import queue
from typing import List, Optional, Union

from ibpy_native import models
from ibpy_native.interfaces import delegates
from ibpy_native.internal import client as ib_client
from ibpy_native.utils import finishable_queue as fq

class AccountsManager(delegates._AccountManagementDelegate):
    """Class to manage all IB accounts under the same username logged-in on
    IB Gateway.
    """
    def __init__(self, accounts: Optional[List[models.Account]] = None):
        self._accounts: List[models.Account] = ([] if accounts is None
                                                else accounts)
        self._account_updates_queue: fq._FinishableQueue = fq._FinishableQueue(
            queue_to_finish=queue.Queue()
        )

    @property
    def accounts(self) -> List[models.Account]:
        """List of IB account(s) available under the same username logged in
        on the IB Gateway.

        Returns:
            List[ibpy_native.account.Account]: List of available IB account(s).
        """
        # Implements `delegates._AccountListDelegate`
        return self._accounts

    @property
    def account_updates_queue(self) -> fq._FinishableQueue:
        """":obj:`ibpy_native.utils.finishable_queue._FinishableQueue`:
        The queue that stores account updates data from IB Gateway.
        """
        return self._account_updates_queue

    def on_account_list_update(self, account_list: List[str]):
        """Callback function for internal API callback
        `_IBWrapper.managedAccounts`.

        Checks the existing account list for update(s) to the list. Terminates
        action(s) or subscription(s) on account(s) which is/are no longer
        available and removes from account list.

        Args:
            account_list (:obj:`List[str]`): List of proceeded account IDs
                updated from IB.
        """
        # Implements `delegates._AccountListDelegate`
        if self._accounts:
            # Deep clone the existing account list for operation as modification
            # while iterating a list will cause unexpected result.
            copied_list = self._accounts.copy()

            for account in self._accounts:
                if account.account_id not in account_list:
                    # Terminates action(s) or subscription(s) on account in
                    # existing account list but not the newly received list.
                    copied_list.remove(account)

            for acc_id in account_list:
                if not any(ac.account_id == acc_id for ac in copied_list):
                    # Adds account appears in received list but not existing
                    # list to the account list so it can be managed by this
                    # framework.
                    copied_list.append(models.Account(account_id=acc_id))

            # Clears the list in instance scope then extends it instead of
            # reassigning its' pointer to the deep cloned list as the original
            # list may be referencing by the user via public property
            # `accounts`.
            self._accounts.clear()
            self._accounts.extend(copied_list)
        else:
            for acc_id in account_list:
                self._accounts.append(models.Account(account_id=acc_id))

    async def sub_account_updates(self, account_id: str):
        """Subscribes to account updates.

        Args:
            account_id (str): The account to subscribe for updates.
        """
        try:
            # Check if the specified account ID is associated with one of the
            # accounts being managed by this account manager.
            account = next(ac for ac in self._accounts
                           if ac.account_id == account_id)
        except StopIteration:
            return

        await self._prevent_multi_account_updates()

        last_elm: Optional[Union[models.RawAccountValueData,
                                 models.RawPortfolioData]] = None

        async for elm in self._account_updates_queue.stream():
            if isinstance(elm, (models.RawAccountValueData,
                                models.RawPortfolioData)):
                if elm.account is not account_id:
                    # Skip the current element incase the data received doesn't
                    # belong to the account specified, which shouldn't happen
                    # at all but just in case.
                    continue

                if isinstance(elm, models.RawAccountValueData):
                    self._update_account_value(account=account, data=elm)
                elif isinstance(elm, models.RawPortfolioData):
                    account.update_portfolio(contract_id=elm.contract.conId,
                                             data=elm)
            elif isinstance(elm, str):
                if last_elm is None:
                    # This case should not happen as the account update time
                    # is always received after the updated data.
                    continue

                if re.fullmatch(r"\d{2}:\d{2}", elm):
                    time = datetime.datetime.strptime(elm, "%H:%M").time()
                    time = time.replace(tzinfo=ib_client._IBClient.TZ)

                    if isinstance(last_elm, (str, models.RawAccountValueData)):
                        # This timestamp represents the last update system time
                        # of the account values updated.
                        account.last_update_time = time
                    elif isinstance(last_elm, models.RawPortfolioData):
                        # This timestamp represents the last update system time
                        # of the portfolio data updated.
                        account.positions[
                            last_elm.contract.conId
                        ].last_update_time = time
            else:
                # In case if there's any unexpected element being passed
                # into this queue.
                continue

            last_elm = elm

    def unsub_account_updates(self):
        """Unsubscribes to account updates."""
        self._account_updates_queue.put(fq._Status.FINISHED)

    #region - Private functions
    async def _prevent_multi_account_updates(self):
        """Prevent multi subscriptions of account updates by verifying the
        `self._account_updates_queue` is finished or not as the API
        `ibapi.EClient.reqAccountUpdates` is designed as only one account at a
        time can be subscribed at a time.
        """
        if self._account_updates_queue.status is fq._Status.INIT:
            # Returns as no account updates request has been made before.
            return

        if not self._account_updates_queue.finished:
            self.unsub_account_updates()

            while not self._account_updates_queue.finished:
                await asyncio.sleep(0.1)

    def _update_account_value(self, account: models.Account,
                              data: models.RawAccountValueData):
        if data.key == "AccountReady":
            account.account_ready = (data.val == "true")
        else:
            account.update_account_value(key=data.key,
                                         currency=data.currency,
                                         val=data.val)
    #endregion - Private functions
