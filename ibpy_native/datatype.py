"""Enums for data type parameter values."""
import enum

@enum.unique
class LiveTicks(enum.Enum):
    """Data types defined for live tick data."""
    ALL_LAST = 'AllLast'
    BID_ASK = 'BidAsk'
    MIDPOINT = 'MidPoint'
    LAST = 'Last'
