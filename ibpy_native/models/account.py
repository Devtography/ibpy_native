"""Models for IB account(s)."""
import datetime
import threading
from typing import Dict, Optional, Union

from ibpy_native.models import portfolio
from ibpy_native.models import raw_data

class Account:
    """Model class for individual IB account.

    Args:
        account_id (str): Account ID received from IB Gateway.
    """
    def __init__(self, account_id: str):
        self._lock = threading.Lock()

        self._account_id = account_id
        self._account_ready = False
        self._account_values: Dict[str, Union[str, Dict[str, str]]] = {}
        self._portfolio: Dict[int, portfolio.Position] = {}
        self._last_update: Optional[datetime.time] = None

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
    def positions(self) -> Dict[int, portfolio.Position]:
        """:obj:`dict` of :obj:`ibpy_native.models.account.Position`:
        Dictionary of positions held by the account this instance representing.
        Using the unique IB contract identifier
        (`ibapi.contract.Contract.ConId`) as key.
        """
        return self._portfolio

    @property
    def last_update_time(self) -> Optional[datetime.time]:
        """:obj:`datetime.time`, optional: The last update system time
        for the account values. `None` if update time is not yet received from
        IB Gateway.
        """
        return self._last_update

    @last_update_time.setter
    def last_update_time(self, val: datetime.time):
        self._last_update = val

    @property
    def destroy_flag(self) -> bool:
        """Flag to indicate if this account instance is going to be destroyed.

        Returns:
            bool: `True` if the corresponding account on IB is no longer
                available. No further action should be perfromed with this
                account instance if it's the case.
        """
        return self._destroy_flag

    def get_account_value(self, key: str, currency: str="") -> Optional[str]:
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

    def update_account_value(self, key: str, currency: str="", val: str=""):
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

    def update_portfolio(self, contract_id: int,
                         data: raw_data.RawPortfolioData):
        """Thread-safe setter function to update the positions held by the
        account the instance is representing.

        Args:
            contract_id (int): The unique IB contract identifier of the contract
                of which a position is held.
            data (:obj:`ibpy_native.models.RawPortfolioData`): The raw profolio
                data received from IB Gateway.
        """
        with self._lock:
            if contract_id in self._portfolio:
                position: portfolio.Position = self._portfolio[contract_id]
                # Updates the existing position object stored in dictionary
                position.contract = data.contract
                position.position = data.position
                position.market_price = data.market_price
                position.market_value = data.market_val
                position.avg_cost = data.avg_cost
                position.unrealised_pnl = data.unrealised_pnl
                position.realised_pnl = data.realised_pnl
            else:
                position = portfolio.Position(contract=data.contract,
                                              pos=data.position,
                                              mk_price=data.market_price,
                                              mk_val=data.market_val,
                                              avg_cost=data.avg_cost,
                                              un_pnl=data.unrealised_pnl,
                                              r_pnl=data.realised_pnl)
                self._portfolio[contract_id] = position

    def destory(self):
        """Marks the instance will be destoried and no further action should be
        performed on this instance.
        """
        with self._lock:
            self._destroy_flag = True
