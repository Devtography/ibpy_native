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

@final
class Position:
    """Thread-safe model class for portfolio data.

    Args:
        contract (:obj:`ibapi.contract.Contract`): The contract for which a
            position is held.
        pos (float): The number of positions held.
        mk_price (float): Instrument's unitary price.
        mk_val (float): Total market value of the instrument.
        avg_cost (float): The average cost of the positions held.
        un_pnl (float): Unrealised profit and loss.
        r_pnl (float): Realised profit and loss.
    """
    def __init__(self, contract: ib_contract.Contract, pos: float,
                 mk_price: float, mk_val: float, avg_cost: float,
                 un_pnl: float, r_pnl: float):
        self._lock = threading.Lock()

        self._contract = contract
        self._pos = pos
        self._mk_price = mk_price
        self._mk_val = mk_val
        self._avg_cost = avg_cost
        self._un_pnl = un_pnl
        self._r_pnl = r_pnl
        self._last_update = ib_client._IBClient.TZ.localize(
            dt=datetime.datetime.now()
        )

    @property
    def contract(self) -> ib_contract.Contract:
        """:obj:`ibapi.contract.Contract`: The contract for which a position
        is held.
        """
        return self._contract

    @property
    def position(self) -> float:
        """float: The number of positions held."""
        return self._pos

    @position.setter
    def position(self, val: float):
        with self._lock:
            self._pos = val

    @property
    def market_price(self) -> float:
        """float: Instrument's unitary price."""
        return self._mk_price

    @market_price.setter
    def market_price(self, val: float):
        with self._lock:
            self._mk_price = val

    @property
    def market_value(self) -> float:
        """float: Total market value of the instrument."""
        return self._mk_val

    @market_value.setter
    def market_value(self, val: float):
        with self._lock:
            self._mk_val = val

    @property
    def avg_cost(self) -> float:
        """float: The average of the positions held."""
        return self._avg_cost

    @avg_cost.setter
    def avg_cost(self, val: float):
        with self._lock:
            self._avg_cost = val

    @property
    def unrealised_pnl(self) -> float:
        """float: Unrealised profit and loss."""
        return self._un_pnl

    @unrealised_pnl.setter
    def unrealised_pnl(self, val: float):
        with self._lock:
            self._un_pnl = val

    @property
    def realised_pnl(self) -> float:
        """float: Realised profit and loss."""
        return self._r_pnl

    @realised_pnl.setter
    def realised_pnl(self, val: float):
        with self._lock:
            self._r_pnl = val

    @property
    def last_update_time(self) -> datetime.datetime:
        """:obj:`datetime.datetime`: The last time on which the position data
        was updated.

        Note:
            This property will always be converted to an aware object
            based on the timezone set via `ibpy_native.bridge.IBBridge.`.
        """
        return self._last_update

    @last_update_time.setter
    def last_update_time(self, val: datetime.datetime):
        converted = ib_client._IBClient.TZ.localize(dt=val)

        with self._lock:
            self._last_update = converted

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
