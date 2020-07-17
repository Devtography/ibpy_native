"""Enums/Types for parameters or return objects."""
import enum
from typing import Union
from typing_extensions import TypedDict

from ibapi import wrapper

@enum.unique
class LiveTicks(enum.Enum):
    """Data types defined for live tick data."""
    ALL_LAST = 'AllLast'
    BID_ASK = 'BidAsk'
    MIDPOINT = 'MidPoint'
    LAST = 'Last'

class HistoricalTicksResult(TypedDict):
    """Use to type hint the returns of `IBBridge.get_historical_ticks`."""
    ticks: Union[
        wrapper.HistoricalTick,
        wrapper.HistoricalTickBidAsk,
        wrapper.HistoricalTickLast
    ]
    completed: bool
