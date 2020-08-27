"""Code implementation of IB API resposes handling."""
# pylint: disable=protected-access
import queue
from typing import Dict, List, Optional, Union

from ibapi import wrapper

from ibpy_native import error
from ibpy_native.interfaces import listeners
from ibpy_native.utils import finishable_queue as fq

class _IBWrapper(wrapper.EWrapper):
    """The wrapper deals with the action coming back from the IB gateway or
    TWS instance.
    """

    _req_queue: Dict[int, fq._FinishableQueue] = {}

    def __init__(self,
                 listener: Optional[listeners.NotificationListener] = None):
        self._listener: Optional[listeners.NotificationListener] = listener

        super().__init__()

    @property
    def next_req_id(self) -> int:
        """The next usable request ID (ticker ID in IB API).

        Finds the next available request ID by looking up if there's any
        finished `_FinishableQueue` in internal queue dictionary `__req_queue`.
        If so, returns the ID of the first finished `_FinishableQueue` found.
        Returns the last ID in `__req_queue` + 1 if otherwise.

        Returns:
            int: The next usable request ID.
        """
        usable_id = 0

        if self._req_queue:
            for key, f_queue in self._req_queue.items():
                if f_queue.finished:
                    return key

                if key > usable_id:
                    usable_id = key

        return usable_id + 1

    def get_request_queue(self, req_id: int) -> fq._FinishableQueue:
        """Initialise queue or returns the existing queue with ID `req_id`.

        Args:
            req_id (int): Request ID (ticker ID in IB API) to associate to the
                queue.

        Returns:
            ibpy_native.utils.finishable_queue._FinishableQueue: The newly
                initialised queue or the already existed queue associated to
                the `req_id`.

        Raises:
            ibpy_native.error.IBError: If `_FinishableQueue` associated with
                `req_id` is being used by other tasks.
        """
        try:
            self.__init_req_queue(req_id=req_id)
        except error.IBError as err:
            raise err

        return self._req_queue[req_id]

    def get_request_queue_no_throw(self, req_id: int) -> \
        Optional[fq._FinishableQueue]:
        """Returns the existing queue with ID `req_id`.

        Args:
            req_id (int): Request ID (ticker ID in IB API) associated to the
                queue.

        Returns:
            Optional[ibpy_native.utils.finishable_queue._FinishableQueue]:
                The existing `_FinishableQueue` associated to the specified
                `req_id`. `None` if `req_id` doesn't match with any existing
                `_FinishableQueue` object.
        """
        return self._req_queue[req_id] if req_id in self._req_queue else None

    # Error handling
    def set_on_notify_listener(self, listener: listeners.NotificationListener):
        """Setter for optional `NotificationListener`.

        Args:
            listener (ibpy_native.interfaces.listeners.NotificationListener):
                Listener for IB notifications.
        """
        self._listener = listener

    def error(self, reqId, errorCode, errorString):
        # override method
        err = error.IBError(rid=reqId, err_code=errorCode, err_str=errorString)

        # -1 indicates a notification and not true error condition
        if reqId is not -1:
            self._req_queue[reqId].put(element=err)
        else:
            if self._listener is not None:
                self._listener.on_notify(msg_code=errorCode, msg=errorString)

    # Get contract details
    def contractDetails(self, reqId, contractDetails):
        # override method
        self._req_queue[reqId].put(element=contractDetails)

    def contractDetailsEnd(self, reqId):
        # override method
        self._req_queue[reqId].put(element=fq._Status.FINISHED)

    # Get earliest data point for a given instrument and data
    def headTimestamp(self, reqId: int, headTimestamp: str):
        # override method
        self._req_queue[reqId].put(element=headTimestamp)
        self._req_queue[reqId].put(element=fq._Status.FINISHED)

    # Fetch historical ticks data
    def historicalTicks(self, reqId: int,
                        ticks: List[wrapper.HistoricalTick], done: bool):
        # override method
        self._handle_historical_ticks_results(reqId, ticks, done)

    def historicalTicksBidAsk(self, reqId: int,
                              ticks: List[wrapper.HistoricalTickBidAsk],
                              done: bool):
        # override method
        self._handle_historical_ticks_results(req_id=reqId, ticks=ticks,
                                              done=done)

    def historicalTicksLast(self, reqId: int,
                            ticks: List[wrapper.HistoricalTickLast],
                            done: bool):
        # override method
        self._handle_historical_ticks_results(req_id=reqId, ticks=ticks,
                                              done=done)

    # Stream live tick data
    def tickByTickAllLast(self, reqId: int, tickType: int, time: int,
                          price: float, size: int,
                          tickAttribLast: wrapper.TickAttribLast,
                          exchange: str, specialConditions: str):
        # override method
        record = wrapper.HistoricalTickLast()
        record.time = time
        record.price = price
        record.size = size
        record.tickAttribLast = tickAttribLast
        record.exchange = exchange
        record.specialConditions = specialConditions

        self._handle_live_ticks(req_id=reqId, tick=record)

    def tickByTickBidAsk(self, reqId: int, time: int, bidPrice: float,
                         askPrice: float, bidSize: int, askSize: int,
                         tickAttribBidAsk: wrapper.TickAttribBidAsk):
        # override method
        record = wrapper.HistoricalTickBidAsk()
        record.time = time
        record.priceBid = bidPrice
        record.sizeBid = bidSize
        record.priceAsk = askPrice
        record.sizeAsk = askSize
        record.tickAttribBidAsk = tickAttribBidAsk

        self._handle_live_ticks(req_id=reqId, tick=record)

    def tickByTickMidPoint(self, reqId: int, time: int, midPoint: float):
        # override method
        record = wrapper.HistoricalTick()
        record.time = time
        record.price = midPoint

        self._handle_live_ticks(req_id=reqId, tick=record)

    ## Private functions
    def __init_req_queue(self, req_id: int):
        """Initials a new `_FinishableQueue` if there's no object at
        `self.__req_queue[req_id]`; Resets the queue status to its' initial
        status.

        Raises:
            ibpy_native.error.IBError: If a `_FinishableQueue` already exists at
                `self.__req_queue[req_id]` and it's not finished.
        """
        if req_id in self._req_queue:
            if self._req_queue[req_id].finished:
                self._req_queue[req_id].reset()
            else:
                raise error.IBError(
                    rid=req_id, err_code=error.IBErrorCode.QUEUE_IN_USE,
                    err_str=f"Requested queue with ID {str(req_id)} is "\
                        "currently in use"
                )
        else:
            self._req_queue[req_id] = fq._FinishableQueue(queue.Queue())

    def _handle_historical_ticks_results(
            self, req_id: int,
            ticks: Union[List[wrapper.HistoricalTick],
                         List[wrapper.HistoricalTickBidAsk],
                         List[wrapper.HistoricalTickLast]],
            done: bool
    ):
        """Handles results return from functions `historicalTicks`,
        `historicalTicksBidAsk`, and `historicalTicksLast` by putting the
        results into corresponding queue & marks the queue as finished.
        """
        self._req_queue[req_id].put(element=ticks)
        self._req_queue[req_id].put(element=done)
        self._req_queue[req_id].put(element=fq._Status.FINISHED)

    def _handle_live_ticks(self, req_id: int,
                           tick: Union[wrapper.HistoricalTick,
                                       wrapper.HistoricalTickBidAsk,
                                       wrapper.HistoricalTickLast]):
        """Handles live ticks passed to functions `tickByTickAllLast`,
        `tickByTickBidAsk`, and `tickByTickMidPoint` by putting the ticks
        received into corresponding queue.
        """
        self._req_queue[req_id].put(element=tick)
