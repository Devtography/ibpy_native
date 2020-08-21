"""Code implementation for `EClient` related stuffs"""
from datetime import datetime, timedelta
from typing import List, Tuple, Union

import pytz
from typing_extensions import Literal, TypedDict

from ibapi.contract import Contract
from ibapi.client import EClient
from ibapi.wrapper import (HistoricalTick, HistoricalTickBidAsk,
                           HistoricalTickLast)
from ibpy_native.error import IBError, IBErrorCode
from ibpy_native.interfaces.listeners import LiveTicksListener
from ibpy_native.utils import const, finishable_queue as fq
from ibpy_native.internal.wrapper import IBWrapper

class _ProcessHistoricalTicksResult(TypedDict):
    """Use for type hint the returns of `IBClient.fetch_historical_ticks`."""
    ticks: List[Union[HistoricalTick, HistoricalTickBidAsk, HistoricalTickLast]]
    next_end_time: datetime

class IBClient(EClient):
    """The client calls the native methods from IBWrapper instead of
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

    async def resolve_contract(self, req_id: int,
                               contract: Contract) -> Contract:
        """From a partially formed contract, returns a fully fledged version.

        Args:
            req_id (int): Request ID (ticker ID in IB API).
            contract (Contract): `Contract` object with partially completed info
                - e.g. symbol, currency, etc...

        Returns:
            Contract: Fully resolved IB contract.

        Raises:
            IBError: If
                - queue associated with `req_id` is being used by other tasks;
                - there's any error returned from IB;
                - no item found in received result.
        """

        # Make place to store the data that will be returned
        try:
            f_queue = self.__wrapper.get_request_queue(req_id)
        except IBError as err:
            raise err

        print("Getting full contract details from IB...")

        self.reqContractDetails(req_id, contract)

        # Run until we get a valid contract(s)
        res = await f_queue.get()

        if res:
            if f_queue.status is fq.Status.ERROR:
                if isinstance(res[-1], IBError):
                    raise res[-1]

                raise IBError(
                    rid=req_id, err_code=IBErrorCode.UNKNOWN,
                    err_str="Unknown error: Internal queue reported error "
                    "status but there is no exception received"
                )

            if len(res) > 1:
                print("Multiple contracts found: returning 1st contract")

            resolved_contract = res[0].contract

            return resolved_contract

        raise IBError(
            req_id, IBErrorCode.RES_NO_CONTENT.value,
            "Failed to get additional contract details"
        )

    async def resolve_head_timestamp(
            self, req_id: int, contract: Contract,
            show: Literal['BID', 'ASK', 'TRADES'] = 'TRADES'
        ) -> int:
        """Fetch the earliest available data point for a given instrument
        from IB.

        Args:
            req_id (int): Request ID (ticker ID in IB API).
            contract (Contract): `Contract` object with sufficient info to
                identify the instrument.
            show (Literal['BID', 'ASK', 'TRADES'], optional):
                Type of data for head timestamp. Defaults to 'TRADES'.

        Returns:
            int: Unix timestamp of the earliest available datapoint.

        Raises:
            IBError: If
                - queue associated with `req_id` is being used by other tasks;
                - there's any error returned from IB;
                - no element found in received result;
                - multiple elements found in received result.
        """
        if show not in {'BID', 'ASK', 'TRADES'}:
            raise ValueError(
                "Value of argument `show` can only be either 'BID', 'ASK', or "
                "'TRADES'"
            )

        try:
            f_queue = self.__wrapper.get_request_queue(req_id)
        except IBError as err:
            raise err

        print("Getting earliest available data point for the given "
              "instrument from IB... ")

        self.reqHeadTimeStamp(req_id, contract, show, 0, 2)

        res = await f_queue.get()

        # Cancel the head time stamp request to release the ID after the
        # request queue is finished
        self.cancelHeadTimeStamp(req_id)

        if res:
            if f_queue.status is fq.Status.ERROR:
                if isinstance(res[-1], IBError):
                    raise res[-1]

                raise IBError(
                    rid=req_id, err_code=IBErrorCode.UNKNOWN,
                    err_str="Unknown error: Internal queue reported error "
                    "status but there is no exception received"
                )

            if len(res) > 1:
                raise IBError(
                    req_id, IBErrorCode.RES_UNEXPECTED.value,
                    "[Abnormal] Multiple result received"
                )

            return int(res[0])

        raise IBError(
            req_id, IBErrorCode.RES_NO_CONTENT.value,
            "Failed to get the earliest available data point"
        )

    async def fetch_historical_ticks(
            self, req_id: int, contract: Contract,
            start: datetime, end: datetime = datetime.now().astimezone(TZ),
            show: Literal['MIDPOINT', 'BID_ASK', 'TRADES'] = 'TRADES'
        ) -> Tuple[List[Union[HistoricalTick,
                              HistoricalTickBidAsk,
                              HistoricalTickLast]],
                   bool]:
        """Fetch the historical ticks data for a given instrument from IB.

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

        if type(start.tzinfo) is not type(end.tzinfo):
            raise ValueError(
                "Timezone of the start time and end time must be the same"
            )

        if start.timestamp() > end.timestamp():
            raise ValueError(
                "Specificed start time cannot be later than end time"
            )

        # Time to fetch the ticks
        try:
            f_queue = self.__wrapper.get_request_queue(req_id)
        except IBError as err:
            raise err

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
                next_end_time.strftime(const.IB.TIME_FMT),
                1000, show, 0, False, []
            )

            res: List[
                List[Union[
                    HistoricalTick,
                    HistoricalTickBidAsk,
                    HistoricalTickLast
                ]],
                bool
            ] = await f_queue.get()

            if res and f_queue.status is fq.Status.ERROR:
                # Response received and internal queue reports error
                if isinstance(res[-1], IBError):
                    if all_ticks:
                        if res[-1].err_code == IBErrorCode.INVALID_CONTRACT:
                            # Continue if IB returns error `No security
                            # definition has been found for the request` as
                            # it's not possible that ticks can be fetched
                            # on pervious attempts for an invalid contract.
                            f_queue.reset()
                            continue

                        # Encounters error. Returns ticks fetched in
                        # pervious loop(s).
                        break

                    res[-1].err_extra = next_end_time
                    raise res[-1]

                raise IBError(
                    rid=req_id, err_code=IBErrorCode.UNKNOWN,
                    err_str="Unknown error: Internal queue reported error "
                    "status but there is no exception received",
                    err_extra=next_end_time
                )

            if res:
                if len(res) != 2:
                    # The result should be a list that contains 2 items:
                    # [ticks: ListOfHistoricalTick(BidAsk/Last), done: bool]
                    if all_ticks:
                        print("Abnormal result received while fetching the "
                              f"remaining ticks: returning {len(all_ticks)} "
                              "ticks fetched")
                        break

                    raise IBError(
                        req_id, IBErrorCode.RES_UNEXPECTED.value,
                        "[Abnormal] Incorrect number of items received: "
                        f"{len(res)}"
                    )

                # Process the data
                processed_result = self.__process_historical_ticks(
                    ticks=res[0],
                    start_time=real_start_time,
                    end_time=next_end_time
                )
                all_ticks.extend(processed_result['ticks'])
                next_end_time = processed_result['next_end_time']

                print(
                    f"{len(all_ticks)} ticks fetched ("
                    f"{len(processed_result['ticks'])} new ticks); Next end "
                    f"time - {next_end_time.strftime(const.IB.TIME_FMT)}"
                )

                if next_end_time.timestamp() <= real_start_time.timestamp():
                    # All tick data within the specificed range has been
                    # fetched from IB. Finishes the while loop.
                    finished = True

                    break

                # Resets the queue for next historical ticks request
                f_queue.reset()

            else:
                if all_ticks:
                    print("Request failed while fetching the remaining ticks: "
                          f"returning {len(all_ticks)} ticks fetched")

                    break

                raise IBError(
                    rid=req_id, err_code=IBErrorCode.RES_NO_CONTENT,
                    err_str="Failed to get historical ticks data"
                )

        all_ticks.reverse()

        return (all_ticks, finished)

    # Stream live tick data
    async def stream_live_ticks(
            self, req_id: int, contract: Contract, listener: LiveTicksListener,
            tick_type: Literal['Last', 'AllLast', 'BidAsk', 'MidPoint'] = 'Last'
        ):
        """Request to stream live tick data.

        Args:
            req_id (int): Request ID (ticker ID in IB API).
            contract (Contract): `Contract` object with partially completed info
                - e.g. symbol, currency, etc...
            listener (LiveTicksListener): Callback listener for receiving ticks,
                finish signal, and error from IB API.
            tick_type (Literal['Last', 'AllLast', 'BidAsk', 'MidPoint'],
                optional): Type of tick to be requested. Defaults to 'Last'.

        Raises:
            IBError: If queue associated with `req_id` is being used by other
                tasks.

        Note:
            The value of `tick_type` is case sensitive - it must be `"BidAsk"`,
            `"Last"`, `"AllLast"`, `"MidPoint"`. `"AllLast"` has additional
            trade types such as combos, derivatives, and average price trades
            which are not included in `"Last"`.
            Also, this function depends on `live_ticks_listener` to return
            live ticks received. The listener should be set explicitly.
        """
        # Error checking
        if tick_type not in {'Last', 'AllLast', 'BidAsk', 'MidPoint'}:
            raise ValueError(
                "Value of argument `tick_type` can only be either 'Last', "
                "'AllLast', 'BidAsk', or 'MidPoint'"
            )

        try:
            f_queue = self.__wrapper.get_request_queue(req_id)
        except IBError as err:
            raise err

        print(f"Streaming live ticks [{tick_type}] for the given instrument "
              "instrument from IB...")

        self.reqTickByTickData(
            reqId=req_id, contract=contract, tickType=tick_type,
            numberOfTicks=0, ignoreSize=True
        )

        async for elem in f_queue.stream():
            if isinstance(
                    elem,
                    (HistoricalTick,
                     HistoricalTickLast,
                     HistoricalTickBidAsk)
                ):
                listener.on_tick_receive(req_id=req_id, tick=elem)
            elif isinstance(elem, IBError):
                listener.on_err(err=elem)
            elif elem is fq.Status.FINISHED:
                listener.on_finish(req_id=req_id)

    def cancel_live_ticks_stream(self, req_id: int):
        """Stop the live tick data stream that's currently streaming.

        Args:
            req_id (int): Request ID (ticker ID in IB API).

        Raises:
            IBError: If there's no `FinishableQueue` object associated with the
                specified `req_id` found in the internal `IBWrapper` object.
        """
        f_queue = self.__wrapper.get_request_queue_no_throw(req_id=req_id)

        if f_queue is not None:
            self.cancelTickByTickData(reqId=req_id)
            f_queue.put(fq.Status.FINISHED)
        else:
            raise IBError(
                rid=req_id, err_code=IBErrorCode.RES_NOT_FOUND,
                err_str=f"Task associated with request ID {req_id} not found"
            )

    # Private functions
    def __process_historical_ticks(
            self, ticks: List[Union[HistoricalTick,
                                    HistoricalTickBidAsk,
                                    HistoricalTickLast]],
            start_time: datetime, end_time: datetime
    ) -> _ProcessHistoricalTicksResult:
        """Processes the tick data returned from IB in function
        `fetch_historical_ticks`.
        """
        if len(ticks) > 0:
            # Exclude record(s) which are earlier than specified start time.
            exclude_to_idx = -1

            for idx, tick in enumerate(ticks):
                if tick.time >= start_time.timestamp():
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

                # Updates the next end time to prepare to fetch more
                # data again from IB
                end_time = datetime.fromtimestamp(
                    ticks[-1].time
                ).astimezone(end_time.tzinfo)
            else:
                # Ticks data received from IB but all records included in
                # response are earlier than the start time.
                ticks = []
                end_time = start_time

        if len(ticks) == 0:
            # Floor the `end_time` to pervious 30 minutes point to avoid IB
            # cutting off the data at the date start point for the instrument.
            # e.g.
            delta = timedelta(minutes=end_time.minute % 30,
                              seconds=end_time.second)

            if delta.total_seconds() == 0:
                end_time = end_time - timedelta(minutes=30)
            else:
                end_time = end_time - delta

        return {
            'ticks': ticks,
            'next_end_time': end_time,
        }
