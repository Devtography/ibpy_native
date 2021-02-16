"""Enums/Types for parameters or return objects."""
import enum
from typing import List, NamedTuple, Union
from typing_extensions import TypedDict

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
class HistoricalTicksResult(TypedDict):
    """Use to type hint the returns of `IBBridge.get_historical_ticks`."""
    ticks: List[Union[
        wrapper.HistoricalTick,
        wrapper.HistoricalTickBidAsk,
        wrapper.HistoricalTickLast
    ]]
    completed: bool

class ResHistoricalTicks(NamedTuple):
    """Return type of function `bridge.IBBridge.get_historical_ticks_v2`."""
    ticks: List[Union[
        wrapper.HistoricalTick,
        wrapper.HistoricalTickBidAsk,
        wrapper.HistoricalTickLast
    ]]
    completed: bool
#endregion - Return type
