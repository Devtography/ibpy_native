import enum

class IBTicks(enum.Enum):
    """
    Types of ticks data defined by IB
    """
    MIDPOINT = "MIDPOINT"
    BID_ASK = "BID_ASK"
    TRADES = "TRADES"