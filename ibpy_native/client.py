from .wrapper import IBWrapper
from .error import IBError, IBErrorCode
from .finishable_queue import FinishableQueue, Status

from ibapi.contract import Contract
from ibapi.client import EClient
from ibapi.wrapper import (HistoricalTick, HistoricalTickBidAsk,
    HistoricalTickLast)
from datetime import datetime
from typing import List, Optional, Tuple, Union
from typing_extensions import Literal

import enum
import pytz

class Const(enum.Enum):
    TIME_FMT = '%Y%m%d %H:%M:%S' # IB time format
    MSG_TIMEOUT = "Exceed maximum wait for wrapper to confirm finished"

class IBClient(EClient):
    """
    The client calls the native methods from IBWrapper instead of
    overriding native methods
    """

    # Static variable to define the timezone
    TZ = pytz.timezone('America/New_York')

    # Default timeout time in second for requests
    REQ_TIMEOUT = 10

    def __init__(self, wrapper: IBWrapper):
        self.__wrapper = wrapper
        super().__init__(wrapper)

    def resolve_contract(
        self, req_id: int, contract: Contract, timeout: int = REQ_TIMEOUT
    ) -> Contract:
        """
        From a partially formed contract, returns a fully fledged version
        :returns fully resolved IB contract
        """

        # Make place to store the data that will be returned
        try:
            queue = self.__wrapper.get_request_queue(req_id)
        except IBError as err:
            raise err

        f_queue = FinishableQueue(queue)

        print("Getting full contract details from IB...")

        self.reqContractDetails(req_id, contract)

        # Run until we get a valid contract(s) or timeout
        contract_details = f_queue.get(timeout=timeout)

        try:
            self.__check_error()
        except IBError as err:
            raise err

        if f_queue.get_status() == Status.TIMEOUT:
            raise IBError(
                req_id, IBErrorCode.REQ_TIMEOUT.value,
                Const.MSG_TIMEOUT.value
            )

        if len(contract_details) == 0:
            raise IBError(
                req_id, IBErrorCode.RES_NO_CONTENT.value,
                "Failed to get additional contract details"
            )

        if len(contract_details) > 1:
            print("Multiple contracts found: returning 1st contract")

        resolved_contract = contract_details[0].contract

        return resolved_contract

    def resolve_head_timestamp(
        self, req_id: int, contract: Contract,
        show: Literal['BID', 'ASK', 'TRADES'] = 'TRADES',
        timeout: int = REQ_TIMEOUT
    ) -> int:
        """
        Fetch the earliest available data point for a given instrument from IB.

        :returns unix timestamp of the earliest available data point
        """
        if show not in {'BID', 'ASK', 'TRADES'}:
            raise ValueError(
                "Value of argument `show` can only be either 'BID', 'ASK', or "
                "'TRADES'"
            )

        try:
            queue = self.__wrapper.get_request_queue(req_id)
        except IBError as err:
            raise err

        f_queue = FinishableQueue(queue)

        print("Getting earliest available data point for the given " 
            "instrument from IB... ")

        self.reqHeadTimeStamp(req_id, contract, show, 0, 2)

        head_timestamp = f_queue.get(timeout=timeout)

        # Cancel the head time stamp request to release the ID after the 
        # request queue is finished/timeout
        self.cancelHeadTimeStamp(req_id)

        try:
            self.__check_error()
        except IBError as err:
            raise err

        if f_queue.get_status() == Status.TIMEOUT:
            raise IBError(
                    req_id, IBErrorCode.REQ_TIMEOUT.value,
                    Const.MSG_TIMEOUT.value
                )

        if len(head_timestamp) == 0:
            raise IBError(
                req_id, IBErrorCode.RES_NO_CONTENT.value,
                "Failed to get the earliest available data point"
            )

        if len(head_timestamp) > 1:
            raise IBError(
                req_id, IBErrorCode.RES_UNEXPECTED.value,
                "[Abnormal] Multiple result received"
            )

        return int(head_timestamp[0])

    def fetch_historical_ticks(
        self, req_id: int, contract: Contract,
        start: Optional[datetime] = None, 
        end: datetime = datetime.now().astimezone(TZ),
        show: Literal['MIDPOINT', 'BID_ASK', 'TRADES'] = 'TRADES',
        timeout: int = REQ_TIMEOUT
    ) -> Tuple[
            List[Union[
                HistoricalTick,
                HistoricalTickBidAsk, 
                HistoricalTickLast
            ]],
            bool
        ]:
        """
        Fetch the historical ticks data for a given instrument from IB.
        
        :returns the ticks data (fetched recursively to get around IB 1000 
        ticks limit)
        """
        # Pre-process & error checking
        if show not in {'MIDPOINT', 'BID_ASK', 'TRADES'}:
            raise ValueError(
                "Value of argument `show` can only be either 'MIDPOINT', "
                "'BID_ASK', or 'TRADES'"
            )

        if start is not None:
            if type(start.tzinfo) != type(end.tzinfo):
                raise ValueError("Timezone of the start time and end time "
                    "must be the same")

            if start.timestamp() > end.timestamp():
                raise ValueError(
                    "Specificed start time cannot be later than end time"
                )
        
        # Time to fetch the ticks
        try:
            queue = self.__wrapper.get_request_queue(req_id)
        except IBError as err:
            raise err

        f_queue = FinishableQueue(queue)

        all_ticks: list = []

        real_start_time = None
        if start is not None:
            real_start_time = (
                IBClient.TZ.localize(start) if start.tzinfo is None
                else start
            )

        next_end_time = (
            IBClient.TZ.localize(end) if end.tzinfo is None else end
        )

        finished = False

        print("Getting historical ticks data [" + show
            + "] for the given instrument from IB...")

        while not finished:
            self.reqHistoricalTicks(
                req_id, contract, "", 
                next_end_time.strftime(Const.TIME_FMT.value), 
                1000, show, 0, False, []
            )

            result: List[
                List[Union[
                    HistoricalTick,
                    HistoricalTickBidAsk, 
                    HistoricalTickLast
                ]],
                bool
            ] = f_queue.get(timeout=timeout)

            # Error checking
            try:
                self.__check_error()
            except IBError as err:
                raise err

            if f_queue.get_status() == Status.TIMEOUT:
                # Checks if it's in the middle of the data fetching loop
                if len(all_ticks) > 0:
                    print("Request timeout while fetching the remaining ticks: "
                        f"returning {str(len(all_ticks))} ticks fetched")
                    # Returns already fetched data instead of having the
                    # pervious time used for fetching data all wasted
                    all_ticks.reverse()

                    return (all_ticks, False)
                else:
                    raise IBError(
                        req_id, IBErrorCode.REQ_TIMEOUT.value,
                        Const.MSG_TIMEOUT.value
                    )

            if len(result) == 0:
                raise IBError(req_id, IBErrorCode.RES_NO_CONTENT.value,
                    "Failed to get historical ticks data")

            if len(result) != 2:
                # The result should be a list that contains 2 items: 
                # [ticks: ListOfHistoricalTick(BidAsk/Last), done: bool]
                raise IBError(req_id, IBErrorCode.RES_UNEXPECTED.value,
                    "[Abnormal] Incorrect number of items received: "
                    + str(len(result)))

            ticks = result[0]

            if len(ticks) == 0 and len(all_ticks) == 0:
                raise IBError(req_id, IBErrorCode.RES_NO_CONTENT.value,
                    "[Abnormal] Request completed without issue but results "
                    "from IB contains no historical ticks data")
            
            # Process the data
            if len(ticks) > 0:
                if real_start_time is not None:
                    # Exclude record(s) which are earlier than specified 
                    # start time
                    exclude_to_idx = 0

                    for idx, tick in enumerate(ticks):
                        if tick.time >= real_start_time.timestamp():
                            exclude_to_idx = idx
                            break
                    del idx, tick

                    if exclude_to_idx > 0:
                        ticks = ticks[exclude_to_idx:]

                # Reverses the list of tick data as the data are fetched 
                # reversely from end time. Thus, reverses the list `ticks` to 
                # append the tick data to `all_ticks` more efficient.
                ticks.reverse()
                all_ticks.extend(ticks)

                print(str(len(all_ticks)) + " ticks fetched; " 
                    "Last tick time - "
                    + (datetime.fromtimestamp(ticks[-1].time)
                        .astimezone(next_end_time.tzinfo)
                        .strftime(Const.TIME_FMT.value)
                    )
                )

            # All ticks data within the specificed range has been fetched from
            # IB, finish the while loop
            if len(ticks) < 1000 and len(all_ticks) > 0:
                finished = True
                break

            # Updates the next end time to fetch the data again if 
            # there's more data to be fetched from IB
            next_end_time = datetime.fromtimestamp(
                ticks[-1].time
            ).astimezone(next_end_time.tzinfo)

            # Resets the queue for next historical ticks request
            f_queue.reset()

        all_ticks.reverse()

        return (all_ticks, True)

    # Private functions
    def __check_error(self):
        """
        Check if the error queue in wrapper contains any error returned from IB
        """
        while self.__wrapper.has_err():
            err: IBError = self.__wrapper.get_err()

            if err.id == -1:
                # -1 means a notification not error
                continue
            else:
                raise err
