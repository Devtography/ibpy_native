"""Model classes of raw data passed from IB Gateway to the wrapper."""
import dataclasses

from typing_extensions import final

from ibapi import contract as ib_contract

@final
@dataclasses.dataclass
class RawAccountValueData:
    """Model class for account value updates received in callback
    `ibpy_native._internal._wrapper.IBWrapper.updateAccountValue`.

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
    `ibpy_native._internal._wrapper.IBWrapper.updatePortfolio`.

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
    position: float
    market_price: float
    market_val: float
    avg_cost: float
    unrealised_pnl: float
    realised_pnl: float
