from .finishable_queue import FinishableQueue, Status
from .error import IBError, IBErrorCode

from ibapi.wrapper import (EWrapper, HistoricalTick, HistoricalTickBidAsk,
    HistoricalTickLast)
from typing import List, Optional, Union

import queue

class IBWrapper(EWrapper):
    """
    The wrapper deals with the action coming back from the IB gateway or 
    TWS instance
    """

    __req_queue = {}

    def __init__(self):
        self.__err_queue = queue.Queue()

        super().__init__()

    def get_request_queue(self, req_id: int) -> queue.Queue:
        """
        Initialise queue or returned the existing queue with ID `req_id`
        """
        self.__init_req_queue(req_id)

        if not self.__req_queue[req_id].empty():
            raise IBError(req_id, IBErrorCode.QUEUE_IN_USE.value,
                f"Request queue with ID {str(req_id)} is currently in use")

        return self.__req_queue[req_id]

    # Error handling
    def has_err(self):
        return not self.__err_queue.empty()
 
    def get_err(self, timeout=10) -> Optional[IBError]:
        if self.has_err():
            try:
                return self.__err_queue.get(timeout=timeout)
            except queue.Empty:
                return None

        return None
       
    def error(self, id, errorCode, errorString):
        # override method
        err = IBError(id, errorCode, errorString)
        
        self.__err_queue.put(err)

        # -1 indicates a notification and not true error condition
        if id is not -1:
            self.__req_queue[id].put(Status.ERROR)

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
