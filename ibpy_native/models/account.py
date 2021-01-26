"""Models for IB account(s)."""
import dataclasses
import threading
from typing import Dict, Optional, Union

from typing_extensions import final, Final

from ibapi import contract as ib_contract

class Account:
    """Model class for individual IB account.

    Attributes:
        account_id (:obj:`Final[str]`): Account ID received from IB Gateway.
    """
    account_id: Final[str]
    _destroy_flag: bool = False

    def __init__(self, account_id: str):
        self._lock = threading.Lock()
        self._account_values: Dict[str, Union[str, Dict[str, str]]] = {}

        self.account_id = account_id

    @property
    def destory_flag(self) -> bool:
        """Flag to indicate if this account instance is going to be destoried.

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
        self._destroy_flag = True

@final
@dataclasses.dataclass
class RawAccountValueData:
    """Model class for account value updates received in callback
    `ibpy_native.internal.wrapper.IBWrapper.updateAccountValue`.

    Attributes:
        account (str): Account ID that the data belongs to.
        currency (str): The currency on which the value is expressed.
        key (str): The value being updated. See `TWS API doc`_ for the full
            list of `key`.
        val (str): Up-to-date value.

    .. _TWS API doc:
        https://interactivebrokers.github.io/tws-api/interfaceIBApi_1_1EWrapper.html#ae15a34084d9f26f279abd0bdeab1b9b5
    """
    account: str
    currency: str
    key: str
    val: str

@final
@dataclasses.dataclass
class RawPortfolioData:
    """Model class for portfolio updates received in callback
    `ibpy_native.internal.wrapper.IBWrapper.updatePortfolio`.

    Attributes:
        account (str): Account ID that the data belongs to.
        contract (:obj:`ibapi.contract.Contract`): The contract for which a
            position is held.
        position (float): The number of positions held.
        market_price (float): Instrument's unitary price.
        market_val (float): Total market value of the instrument.
        avg_cost (float): The average cost of the positions held.
        unrealised_pnl (float): Unrealised profit and loss.
        realised_pnl (float): Realised profit and loss.
    """
    account: str
    contract: ib_contract.Contract
    market_price: float
    market_val: float
    avg_cost: float
    unrealised_pnl: float
    realised_pnl: float
