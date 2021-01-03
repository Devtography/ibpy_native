"""IB account related resources."""
# pylint: disable=protected-access
from typing import List, Optional

from ibpy_native import models
from ibpy_native.interfaces import delegates

class AccountsManager(delegates._AccountListDelegate):
    """Class to manage all IB accounts under the same username logged-in on
    IB Gateway.
    """
    def __init__(self, accounts: Optional[List[models.Account]] = None):
        self._accounts: List[models.Account] = ([] if accounts is None
                                                else accounts)

    @property
    def accounts(self) -> List[models.Account]:
        """List of IB account(s) available under the same username logged in
        on the IB Gateway.

        Returns:
            List[ibpy_native.account.Account]: List of available IB account(s).
        """
        # Implements `delegates._AccountListDelegate`
        return self._accounts

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
