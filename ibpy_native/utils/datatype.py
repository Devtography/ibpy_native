"""Enums/Types for parameters or return objects."""
import enum
from typing import List, NamedTuple, Union

from ibapi import wrapper

#region - Argument options
@enum.unique
class EarliestDataPoint(enum.Enum):
    """Data type options defined for earliest data point."""
    BID = "BID"
    ASK = "ASK"
    TRADES = "TRADES"

@enum.unique
class HistoricalTicks(enum.Enum):
    """Data type options defined for fetching historical ticks."""
    BID_ASK = "BID_ASK"
    MIDPOINT = "MIDPOINT"
    TRADES = "TRADES"

@enum.unique
class LiveTicks(enum.Enum):
    """Data types defined for live tick data."""
    ALL_LAST = "AllLast"
    BID_ASK = "BidAsk"
    MIDPOINT = "MidPoint"
    LAST = "Last"
#endregion - Argument options

#region - Return type
class ResHistoricalTicks(NamedTuple):
    """Return type of function `bridge.IBBridge.get_historical_ticks_v2`."""
    ticks: List[Union[
        wrapper.HistoricalTick,
        wrapper.HistoricalTickBidAsk,
        wrapper.HistoricalTickLast
    ]]
    completed: bool
#endregion - Return type

#region - Order related
@enum.unique
class OrderAction(enum.Enum):
    """Action type of the order. Either BUY or SELL."""
    BUY = "BUY"
    SELL = "SELL"

@enum.unique
class OrderStatus(enum.Enum):
    """Status of the order after submission to TWS/Gateway.

    For the definition of each status, please refer to `Possible Order States`_
    from TWS API document.

    .. _Possible Order States:
        https://interactivebrokers.github.io/tws-api/order_submission.html#order_status
    """
    API_PENDING = "ApiPending"
    PENDING_SUBMIT = "PendingSubmit"
    PENDING_CANCEL = "PendingCancel"
    PRE_SUBMITTED = "PreSubmitted"
    SUBMITTED = "Submitted"
    API_CANCELLED = "ApiCancelled"
    CANCELLED = "Cancelled"
    FILLED = "Filled"
    INACTIVE = "Inactive"
#endregion - Order related
