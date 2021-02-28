"""Model classes for account portfolio related data."""
# pylint: disable=too-many-instance-attributes
import datetime
import threading
from typing import Optional

from typing_extensions import final

from ibapi import contract as ib_contract

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
        self._last_update: Optional[datetime.time] = None

    @property
    def contract(self) -> ib_contract.Contract:
        """:obj:`ibapi.contract.Contract`: The contract for which a position
        is held.
        """
        return self._contract

    @contract.setter
    def contract(self, val: contract):
        with self._lock:
            self._contract = val

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
    def last_update_time(self) -> Optional[datetime.time]:
        """:obj:`datetime.time`: The last time on which the position data
        was updated. `None` if the update time is not yet received from IB
        Gateway.
        """
        return self._last_update

    @last_update_time.setter
    def last_update_time(self, val: datetime.time):
        with self._lock:
            self._last_update = val
