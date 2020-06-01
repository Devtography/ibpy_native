"""
Code implementation for `EClient` related stuffs
"""
import enum
from datetime import datetime, timedelta
from typing import List, Tuple, Union

import pytz
from typing_extensions import Literal

from ibapi.contract import Contract
from ibapi.client import EClient
from ibapi.wrapper import (HistoricalTick, HistoricalTickBidAsk,
                           HistoricalTickLast)
from .wrapper import IBWrapper
from .error import IBError, IBErrorCode
from .finishable_queue import FinishableQueue, Status

class Const(enum.Enum):
    """
    Constants used in `IBClient`
    """
    TIME_FMT = '%Y%m%d %H:%M:%S' # IB time format
    MSG_TIMEOUT = "Exceed maximum wait for wrapper to confirm finished"

class IBClient(EClient):
    """
    The client calls the native methods from IBWrapper instead of
    overriding native methods.

    Attributes:
        TZ: Class level timezone for all datetime related object. Timezone
            should be aligned with the timezone specified in TWS/IB Gateway
            at login. Defaults to 'America/New_York'.
        REQ_TIMEOUT (int): Constant uses as a default timeout value.
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
        From a partially formed contract, returns a fully fledged version.

        Args:
            req_id (int): Request ID (ticker ID in IB API).
            contract (Contract): `Contract` object with partially completed info
                - e.g. symbol, currency, etc...
            timeout (int, optional): Second(s) to wait for the request. Defaults
                to 10.

        Returns:
            Contract: Fully resolved IB contract.

        Raises:
            IBError: If
                - queue associated with `req_id` is being used by other tasks;
                - there's any error returned from IB;
                - request timeout;
                - no item found in received result.
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

        Args:
            req_id (int): Request ID (ticker ID in IB API).
            contract (Contract): `Contract` object with sufficient info to
                identify the instrument.
            show (Literal['BID', 'ASK', 'TRADES'], optional):
                Type of data for head timestamp. Defaults to 'TRADES'.
            timeout (int, optional): Second(s) to wait for the request. Defaults
                to 10.

        Returns:
            int: Unix timestamp of the earliest available datapoint.

        Raises:
            IBError: If
                - queue associated with `req_id` is being used by other tasks;
                - there's any error returned from IB;
                - request timeout;
                - no element found in received result;
                - multiple elements found in received result.
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
            start: datetime, end: datetime = datetime.now().astimezone(TZ),
            show: Literal['MIDPOINT', 'BID_ASK', 'TRADES'] = 'TRADES',
            timeout: int = REQ_TIMEOUT
        ) -> Tuple[
            List[
                Union[
                    HistoricalTick,
                    HistoricalTickBidAsk,
                    HistoricalTickLast
                ]
            ],
            bool
        ]:
        # pylint: disable=unidiomatic-typecheck
        """
        Fetch the historical ticks data for a given instrument from IB.

        Args:
            req_id (int): Request ID (ticker ID in IB API).
            contract (Contract): `Contract` object with sufficient info to
                identify the instrument.
            start (datetime): The time for the earliest tick data to be
                included.
            end (datetime, optional): The time for the latest tick data to be
                included. Defaults to now.
            show (Literal['MIDPOINT', 'BID_ASK', 'TRADES'], optional):
                Type of data requested. Defaults to 'TRADES'.
            timeout (int, optional): Second(s) to wait for each historical ticks
                API request to IB server. Defaults to 10.

        Returns:
            Ticks data (fetched recursively to get around IB 1000 ticks limit)

        Raises:
            ValueError: If
                - `show` is not 'MIDPOINT', 'BIDASK' or 'TRADES';
                - `tzinfo` of `start` & `end` do not align;
                - Value of start` > `end`.
            IBError: If
                - queue associated with `req_id` is being used by other tasks;
                - there's any error returned from IB before any tick data is
                fetched successfully;
                - request timeout with no tick fetched in pervious request(s);
                - no result received from IB with no tick fetched in pervious
                request(s);
                - incorrect number of items (!= 2) found in the result received
                from IB with no tick fetched in pervious request(s).
        """
        # Pre-process & error checking
        if show not in {'MIDPOINT', 'BID_ASK', 'TRADES'}:
            raise ValueError(
                "Value of argument `show` can only be either 'MIDPOINT', "
                "'BID_ASK', or 'TRADES'"
            )

        if type(start.tzinfo) != type(end.tzinfo):
            raise ValueError(
                "Timezone of the start time and end time must be the same"
            )

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

        real_start_time = (
            IBClient.TZ.localize(start) if start.tzinfo is None else start
        )

        next_end_time = (
            IBClient.TZ.localize(end) if end.tzinfo is None else end
        )

        finished = False

        print(f"Getting historical ticks data [{show}] for the given"
              " instrument from IB...")

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
                if len(all_ticks) > 0:
                    if err.err_code == IBErrorCode.INVALID_CONTRACT:
                        # Continue if IB returns error `No security definition
                        # has been found for the request` as it's not possible
                        # that ticks can be fetched on pervious attempts for an
                        # invalid contract.
                        f_queue.reset()
                        continue

                    break

                raise IBError(err.rid, err.err_code, err.err_str,
                              err_extra=next_end_time)

            if f_queue.get_status() == Status.TIMEOUT:
                # Checks if it's in the middle of the data fetching loop
                if len(all_ticks) > 0:
                    print("Request timeout while fetching the remaining ticks: "
                          f"returning {len(all_ticks)} ticks fetched")

                    # Breaks the while loop to return already fetched data
                    # instead of having the pervious time used for fetching
                    # data all wasted
                    break

                raise IBError(
                    req_id, IBErrorCode.REQ_TIMEOUT.value,
                    Const.MSG_TIMEOUT.value
                )

            if len(result) == 0:
                if len(all_ticks) > 0:
                    print("Request failed while fetching the remaining ticks: "
                          f"returning {len(all_ticks)} ticks fetched")

                    break

                raise IBError(
                    req_id, IBErrorCode.RES_NO_CONTENT.value,
                    "Failed to get historical ticks data"
                )

            if len(result) != 2:
                # The result should be a list that contains 2 items:
                # [ticks: ListOfHistoricalTick(BidAsk/Last), done: bool]
                if len(all_ticks) > 0:
                    print("Abnormal result received while fetching the "
                          f"remaining ticks: returning {len(all_ticks)} ticks "
                          "fetched")

                    break

                raise IBError(
                    req_id, IBErrorCode.RES_UNEXPECTED.value,
                    "[Abnormal] Incorrect number of items received: "
                    f"{len(result)}"
                )

            ticks = result[0]

            # Process the data
            if len(ticks) > 0:
                # Exclude record(s) which are earlier than specified
                # start time
                exclude_to_idx = -1

                for idx, tick in enumerate(ticks):
                    if tick.time >= real_start_time.timestamp():
                        exclude_to_idx = idx
                        del idx, tick

                        break

                if exclude_to_idx > -1:
                    if exclude_to_idx > 0:
                        ticks = ticks[exclude_to_idx:]

                    # Reverses the list of tick data as the data are fetched
                    # reversely from end time. Thus, reverses the list `ticks`
                    # to append the tick data to `all_ticks` more efficient.
                    ticks.reverse()
                    all_ticks.extend(ticks)

                    # Updates the next end time to prepare to fetch more
                    # data again from IB
                    next_end_time = datetime.fromtimestamp(
                        ticks[-1].time
                    ).astimezone(next_end_time.tzinfo)

                    print(
                        f"{len(all_ticks)} ticks fetched ({len(ticks)} new "
                        "ticks); Next end time - "
                        f"{next_end_time.strftime(Const.TIME_FMT.value)}"
                    )
                else:
                    # Ticks data received from IB but all records included in
                    # response are earlier than the start time.
                    next_end_time = real_start_time

            if len(ticks) == 0:
                # Floor the `next_end_time` to pervious 30 minutes point
                # to avoid IB cutting off the data at the date start point for
                # the instrument.
                # e.g.
                delta = timedelta(minutes=next_end_time.minute % 30,
                                  seconds=next_end_time.second)

                if delta.total_seconds() == 0:
                    next_end_time = next_end_time - timedelta(minutes=30)
                else:
                    next_end_time = next_end_time - delta

                print(
                    f"{len(all_ticks)} ticks fetched (0 new tick); Next end"
                    f"time - {next_end_time.strftime(Const.TIME_FMT.value)}"
                )

            if next_end_time.timestamp() <= real_start_time.timestamp():
                # All tick data within the specificed range has been
                # fetched from IB. Finish the while loop.
                finished = True

                break

            # Resets the queue for next historical ticks request
            f_queue.reset()

        all_ticks.reverse()

        return (all_ticks, finished)

    # Private functions
    def __check_error(self):
        """
        Check if the error queue in wrapper contains any error returned from IB
        """
        while self.__wrapper.has_err():
            err: IBError = self.__wrapper.get_err()

            if err.rid == -1:
                # -1 means a notification not error
                continue

            raise err
