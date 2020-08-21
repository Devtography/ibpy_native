"""Code implementation of IB API resposes handling."""
import queue
from typing import Dict, List, Optional, Union

from ibapi.wrapper import (EWrapper, HistoricalTick, HistoricalTickBidAsk,
                           HistoricalTickLast, TickAttribBidAsk, TickAttribLast)
from ibpy_native.interfaces.listeners import NotificationListener

from ibpy_native import error
from ibpy_native.utils import finishable_queue as fq

class IBWrapper(EWrapper):
    """The wrapper deals with the action coming back from the IB gateway or
    TWS instance.
    """

    __req_queue: Dict[int, fq.FinishableQueue] = {}

    def __init__(self, listener: Optional[NotificationListener] = None):
        self.__listener: Optional[NotificationListener] = listener

        super().__init__()

    def get_request_queue(self, req_id: int) -> fq.FinishableQueue:
        """Initialise queue or returns the existing queue with ID `req_id`.

        Args:
            req_id (int): Request ID (ticker ID in IB API) to associate to the
                queue.

        Returns:
            FinishableQueue: The newly initialised queue or the already existed
                queue associated to the `req_id`.

        Raises:
            IBError: If `FinishableQueue` associated with `req_id` is being
                used by other tasks.
        """
        try:
            self.__init_req_queue(req_id)
        except error.IBError as err:
            raise err

        return self.__req_queue[req_id]

    def get_request_queue_no_throw(self, req_id: int) -> \
        Optional[fq.FinishableQueue]:
        """Returns the existing queue with ID `req_id`.

        Args:
            req_id (int): Request ID (ticker ID in IB API) associated to the
                queue.

        Returns:
            Optional[FinishableQueue]: The existing `FinishableQueue` associated
                to the specified `req_id`. `None` if `req_id` doesn't match with
                any existing `FinishableQueue` object.
        """
        return self.__req_queue[req_id] if req_id in self.__req_queue else None

    # Error handling
    def set_on_notify_listener(self, listener: NotificationListener):
        """Setter for optional `NotificationListener`.

        Args:
            listener (NotificationListener): Listener for IB notifications.
        """
        self.__listener = listener

    def error(self, reqId, errorCode, errorString):
        # override method
        # This section should be changed prior to version 1.0.0 to optimise
        # memory usage.
        err = error.IBError(reqId, errorCode, errorString)

        # -1 indicates a notification and not true error condition
        if reqId is not -1:
            self.__req_queue[reqId].put(err)
        else:
            if self.__listener is not None:
                self.__listener.on_notify(msg_code=errorCode, msg=errorString)

    # Get contract details
    def contractDetails(self, reqId, contractDetails):
        # override method
        self.__req_queue[reqId].put(contractDetails)

    def contractDetailsEnd(self, reqId):
        # override method
        self.__req_queue[reqId].put(fq.Status.FINISHED)

    # Get earliest data point for a given instrument and data
    def headTimestamp(self, reqId: int, headTimestamp: str):
        # override method
        self.__req_queue[reqId].put(headTimestamp)
        self.__req_queue[reqId].put(fq.Status.FINISHED)

    # Fetch historical ticks data
    def historicalTicks(
            self, reqId: int, ticks: List[HistoricalTick], done: bool
        ):
        # override method
        self.__handle_historical_ticks_results(reqId, ticks, done)

    def historicalTicksBidAsk(
            self, reqId: int, ticks: List[HistoricalTickBidAsk], done: bool
        ):
        # override method
        self.__handle_historical_ticks_results(reqId, ticks, done)

    def historicalTicksLast(
            self, reqId: int, ticks: List[HistoricalTickLast], done: bool
        ):
        # override method
        self.__handle_historical_ticks_results(reqId, ticks, done)

    # Stream live tick data
    def tickByTickAllLast(
            self, reqId: int, tickType: int, time: int, price: float,
            size: int, tickAttribLast: TickAttribLast, exchange: str,
            specialConditions: str
    ):
        # override method
        record = HistoricalTickLast()
        record.time = time
        record.price = price
        record.size = size
        record.tickAttribLast = tickAttribLast
        record.exchange = exchange
        record.specialConditions = specialConditions

        self.__handle_live_ticks(req_id=reqId, tick=record)

    def tickByTickBidAsk(
            self, reqId: int, time: int, bidPrice: float, askPrice: float,
            bidSize: int, askSize: int, tickAttribBidAsk: TickAttribBidAsk
    ):
        # override method
        record = HistoricalTickBidAsk()
        record.time = time
        record.priceBid = bidPrice
        record.sizeBid = bidSize
        record.priceAsk = askPrice
        record.sizeAsk = askSize
        record.tickAttribBidAsk = tickAttribBidAsk

        self.__handle_live_ticks(req_id=reqId, tick=record)

    def tickByTickMidPoint(self, reqId: int, time: int, midPoint: float):
        # override method
        record = HistoricalTick()
        record.time = time
        record.price = midPoint

        self.__handle_live_ticks(req_id=reqId, tick=record)

    ## Private functions
    def __init_req_queue(self, req_id: int):
        """Initials a new `FinishableQueue` if there's no object at
        `self.__req_queue[req_id]`; Resets the queue status to its' initial
        status.

        Raises:
            IBError: If a `FinishableQueue` already exists at
                `self.__req_queue[req_id]` and it's not finished.
        """
        if req_id in self.__req_queue:
            if self.__req_queue[req_id].finished:
                self.__req_queue[req_id].reset()
            else:
                raise error.IBError(
                    rid=req_id, err_code=error.IBErrorCode.QUEUE_IN_USE,
                    err_str=f"Requested queue with ID {str(req_id)} is "\
                        "currently in use"
                )
        else:
            self.__req_queue[req_id] = fq.FinishableQueue(queue.Queue())

    def __handle_historical_ticks_results(
            self,
            req_id: int,
            ticks: Union[
                List[HistoricalTick],
                List[HistoricalTickBidAsk],
                List[HistoricalTickLast]
            ],
            done: bool
    ):
        """Handles results return from functions `historicalTicks`,
        `historicalTicksBidAsk`, and `historicalTicksLast` by putting the
        results into corresponding queue & marks the queue as finished.
        """
        self.__req_queue[req_id].put(ticks)
        self.__req_queue[req_id].put(done)
        self.__req_queue[req_id].put(fq.Status.FINISHED)

    def __handle_live_ticks(
            self, req_id: int,
            tick: Union[
                HistoricalTick,
                HistoricalTickBidAsk,
                HistoricalTickLast
            ]
    ):
        """Handles live ticks passed to functions `tickByTickAllLast`,
        `tickByTickBidAsk`, and `tickByTickMidPoint` by putting the ticks
        received into corresponding queue.
        """
        self.__req_queue[req_id].put(tick)
