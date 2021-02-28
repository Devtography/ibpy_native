"""Internal type aliases for cleaner code."""
from typing import List, Union

from ibapi import wrapper

from ibpy_native import error

HistoricalTickTypes = Union[wrapper.HistoricalTick,
                            wrapper.HistoricalTickBidAsk,
                            wrapper.HistoricalTickLast,]

ResHistoricalTicks = Union[List[wrapper.HistoricalTick],
                           List[wrapper.HistoricalTickBidAsk],
                           List[wrapper.HistoricalTickLast],]

WrapperResHistoricalTicks = List[Union[ResHistoricalTicks, bool, error.IBError]]
