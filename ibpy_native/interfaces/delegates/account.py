"""Internal delegate module for accounts & portfolio related features."""
import abc
from typing import Dict, List

from ibpy_native import models
from ibpy_native.utils import finishable_queue as fq

class AccountsManagementDelegate(metaclass=abc.ABCMeta):
    """Internal delegate protocol for accounts & portfolio related features."""
    @property
    @abc.abstractmethod
    def accounts(self) -> Dict[str, models.Account]:
        """Abstract getter of a list of `Account` instance.

        This property should be implemented to return the IB account list.
        """
        return NotImplemented

    @property
    @abc.abstractmethod
    def account_updates_queue(self) -> fq.FinishableQueue:
        """Abstract getter of the queue designed to handle account updates
        data from IB gateway.

        This property should be implemented to return the `FinishableQueue`
        object.
        """
        return NotImplemented

    @abc.abstractmethod
    def on_account_list_update(self, account_list: List[str]):
        """Callback on `IBWrapper.managedAccounts` is triggered by IB API.

        Args:
            account_list (:obj:`List[str]`): List of proceeded account IDs
                updated from IB.
        """
        return NotImplemented

    @abc.abstractmethod
    async def sub_account_updates(self, account: models.Account):
        """Abstract function to start receiving account updates from IB
        Gateway.

        Args:
            account (:obj:`ibpy_native.models.Account`): The account to
                subscribe for updates.
        """
        return NotImplemented

    @abc.abstractmethod
    async def unsub_account_updates(self):
        """Abstract function to stop receiving account updates from IB Gateway
        from an on-going account updates subscription.
        """
        return NotImplemented

    @abc.abstractmethod
    def on_disconnected(self):
        """INTERNAL FUNCTION! Callback for the event of API connection dropped.
        """
        return NotImplemented
