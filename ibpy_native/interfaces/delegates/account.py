"""Internal delegate module for accounts & portfolio related features."""
# pylint: disable=protected-access
import abc
from typing import List

from ibpy_native import models
from ibpy_native.utils import finishable_queue as fq

class _AccountListDelegate(metaclass=abc.ABCMeta):
    """Internal delegate protocol for accounts & portfolio related features."""
    @property
    @abc.abstractmethod
    def accounts(self) -> List[models.Account]:
        """Abstract getter of a list of `Account` instance.

        This property should be implemented to return the IB account list.
        """
        return NotImplemented

    @property
    @abc.abstractmethod
    def account_updates_queue(self) -> fq._FinishableQueue:
        """Abstract getter of the queue designed to handle account updates
        data from IB gateway.

        This property should be implemented to return the `_FinishableQueue`
        object.
        """
        return NotImplemented

    @abc.abstractmethod
    def on_account_list_update(self, account_list: List[str]):
        """Callback on `_IBWrapper.managedAccounts` is triggered by IB API.

        Args:
            account_list (:obj:`List[str]`): List of proceeded account IDs
                updated from IB.
        """
        return NotImplemented
