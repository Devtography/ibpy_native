"""Models for IB account(s)."""
# pylint: disable=protected-access, too-many-instance-attributes
import dataclasses
import datetime
import threading
from typing import Dict, Optional, Union

from typing_extensions import final

from ibapi import contract as ib_contract
from ibpy_native.internal import client as ib_client

class Account:
    """Model class for individual IB account."""

    def __init__(self, account_id: str):
        self._lock = threading.Lock()

        self._account_id = account_id
        self._account_ready = False
        self._account_values: Dict[str, Union[str, Dict[str, str]]] = {}
        self._destroy_flag = False

    @property
    def account_id(self) -> str:
        """str: Account ID received from IB Gateway."""
        return self._account_id

    @property
    def account_ready(self) -> bool:
        """bool: If false, the account value stored can be out of date or
        incorrect.
        """
        return self._account_ready

    @account_ready.setter
    def account_ready(self, status: bool):
        with self._lock:
            self._account_ready = status

    @property
    def destroy_flag(self) -> bool:
        """Flag to indicate if this account instance is going to be destroyed.

        Returns:
            bool: `True` if the corresponding account on IB is no longer
                available. No further action should be perfromed with this
                account instance if it's the case.
        """
        return self._destroy_flag

    def get_account_value(self, key: str, currency: str = "") -> Optional[str]:
        """Returns the value of specified account's information.

        Args:
            key (str): The account info to retrieve.
            currency (:obj:`str`, optional): The currency on which the value
                is expressed. Defaults to empty string.

        Returns:
            :obj:`str`, optional: Value of specified account's information.
                `None` if no info found with the specified `key` & `currency`.
        """
        if key in self._account_values:
            if currency in self._account_values[key]:
                return self._account_values[key] if (
                    isinstance(self._account_values[key], str)
                ) else self._account_values[key][currency]

        return None

    def update_account_value(self, key: str, currency: str = "", val: str = ""):
        """Thread-safe setter function to update the account value.

        Args:
            key (str): The value being updated.
            currency (:obj:`str`, optional): The currency on which the value
                is expressed. Defaults to empty string.
            val (:obj:`str`, optional): Up-to-date value. Defaults to empty
                string.
        """
        with self._lock:
            if not currency:
                self._account_values[key] = val
            else:
                if key not in self._account_values:
                    self._account_values[key]: Dict[str, str] = {}

                self._account_values[key][currency] = val

    def destory(self):
        """Marks the instance will be destoried and no further action should be
        performed on this instance.
        """
        with self._lock:
            self._destroy_flag = True
