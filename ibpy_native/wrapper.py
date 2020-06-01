"""
code implementation of IB API resposes handling.
"""
import queue
from typing import List, Optional, Union

from ibapi.wrapper import (EWrapper, HistoricalTick, HistoricalTickBidAsk,
                           HistoricalTickLast)

from .finishable_queue import Status
from .error import IBError, IBErrorCode

class IBWrapper(EWrapper):
    """
    The wrapper deals with the action coming back from the IB gateway or
    TWS instance.
    """

    __req_queue = {}

    def __init__(self):
        self.__err_queue = queue.Queue()

        super().__init__()

    def get_request_queue(self, req_id: int) -> queue.Queue:
        """
        Initialise queue or returns the existing queue with ID `req_id`.

        Args:
            req_id (int): Request ID (ticker ID in IB API) to associate to the
                queue.

        Returns:
            queue.Queue: The newly initialised queue or the already existed
                queue associated to the `req_id`.
        """
        self.__init_req_queue(req_id)

        if not self.__req_queue[req_id].empty():
            raise IBError(
                req_id, IBErrorCode.QUEUE_IN_USE.value,
                f"Request queue with ID {str(req_id)} is currently in use"
            )

        return self.__req_queue[req_id]

    # Error handling
    def has_err(self) -> bool:
        """
        Check if there's any error in the error queue.

        Returns:
            bool: Indicates if the error queue contains any error or not.
        """
        return not self.__err_queue.empty()

    def get_err(self, timeout=10) -> Optional[IBError]:
        """
        Get the error from error queue.

        Args:
            timeout (int, optional): Second(s) to wait for the get request.
                Defaults to 10.

        Returns:
            `IBError` if there's any in the error queue;
            `None` if there is no error.
        """
        if self.has_err():
            try:
                return self.__err_queue.get(timeout=timeout)
            except queue.Empty:
                return None

        return None

    def error(self, reqId, errorCode, errorString):
        # override method
        err = IBError(reqId, errorCode, errorString)

        self.__err_queue.put(err)

        # -1 indicates a notification and not true error condition
        if reqId is not -1:
            self.__req_queue[reqId].put(Status.ERROR)

    # Get contract details
    def contractDetails(self, reqId, contractDetails):
        # override method
        self.__init_req_queue(reqId)

        self.__req_queue[reqId].put(contractDetails)

    def contractDetailsEnd(self, reqId):
        # override method
        self.__init_req_queue(reqId)

        self.__req_queue[reqId].put(Status.FINISHED)

    # Get earliest data point for a given instrument and data
    def headTimestamp(self, reqId: int, headTimestamp: str):
        # override method
        self.__init_req_queue(reqId)

        self.__req_queue[reqId].put(headTimestamp)
        self.__req_queue[reqId].put(Status.FINISHED)

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

    ## Private functions
    def __init_req_queue(self, req_id: int):
        """
        Initial a new queue if there's no queue at `__req_queue[req_id]`
        """
        if req_id not in self.__req_queue.keys():
            self.__req_queue[req_id] = queue.Queue()

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
        """
        Handles results return from functions `historicalTicks`,
        `historicalTicksBidAsk`, and `historicalTicksLast` by putting the
        results into corresponding queue & marks the queue as finished.
        """
        self.__init_req_queue(req_id)

        self.__req_queue[req_id].put(ticks)
        self.__req_queue[req_id].put(done)
        self.__req_queue[req_id].put(Status.FINISHED)
