"""Code implementation for `EClient` related stuffs"""
# pylint: disable=protected-access
import datetime
from typing import Any, List, Optional, Union

import pytz
from typing_extensions import TypedDict

from ibapi import client as ib_client
from ibapi import contract as ib_contract
from ibapi import wrapper as ib_wrapper

from ibpy_native import error
from ibpy_native.interfaces import listeners
from ibpy_native.internal import wrapper as ibpy_wrapper
from ibpy_native.utils import const
from ibpy_native.utils import datatype as dt
from ibpy_native.utils import finishable_queue as fq

class _ProcessHistoricalTicksResult(TypedDict):
    """Use for type hint the returns of `_IBClient.fetch_historical_ticks`."""
    ticks: List[Union[ib_wrapper.HistoricalTick,
                      ib_wrapper.HistoricalTickBidAsk,
                      ib_wrapper.HistoricalTickLast]]
    next_end_time: datetime.datetime

class _IBClient(ib_client.EClient):
    """The client calls the native methods from _IBWrapper instead of
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

    def __init__(self, wrapper: ibpy_wrapper._IBWrapper):
        self._wrapper = wrapper
        super().__init__(wrapper)

    async def resolve_contract(
            self, req_id: int, contract: ib_contract.Contract
        ) -> ib_contract.Contract:
        """From a partially formed contract, returns a fully fledged version.

        Args:
            req_id (int): Request ID (ticker ID in IB API).
            contract (:obj:`ibapi.contract.Contract`):
                `Contract` object with partially completed info
                    - e.g. symbol, currency, etc...

        Returns:
            ibapi.contract.Contract: Fully resolved IB contract.

        Raises:
            ibpy_native.error.IBError: If
                - queue associated with `req_id` is being used by other tasks;
                - there's any error returned from IB;
                - no item found in received result.
        """

        # Make place to store the data that will be returned
        try:
            f_queue = self._wrapper.get_request_queue(req_id=req_id)
        except error.IBError as err:
            raise err

        print("Getting full contract details from IB...")

        self.reqContractDetails(reqId=req_id, contract=contract)

        # Run until we get a valid contract(s)
        res = await f_queue.get()

        if res:
            if f_queue.status is fq._Status.ERROR:
                if isinstance(res[-1], error.IBError):
                    raise res[-1]

                raise self._unknown_error(req_id=req_id)

            if len(res) > 1:
                print("Multiple contracts found: returning 1st contract")

            resolved_contract = res[0].contract

            return resolved_contract

        raise error.IBError(
            rid=req_id, err_code=error.IBErrorCode.RES_NO_CONTENT,
            err_str="Failed to get additional contract details"
        )

    async def resolve_contracts(
            self, req_id: int, contract: ib_contract.Contract
        ) -> List[ib_contract.ContractDetails]:
        """Search the fully fledged contracts with details from a partially
        formed `ibapi.contract.Contract` object.

        Args:
            req_id (int): Request ID (ticker ID in IB API).
            contract (:obj:`ibapi.contract.Contract`): `Contract` object with
                partially completed info
                    - e.g. symbol, currency, etc...

        Returns:
            List[ibapi.contract.ContractDetails]: Fully fledged IB contract(s)
                with detailed info.

        Raises:
            ibpy_native.error.IBError: If
                - queue associated with `req_id` is being used by other tasks;
                - there's any error returned from IB;
                - no item found in received result.
        """
        # Prepare queue to store the data that will be returned
        try:
            f_queue = self._wrapper.get_request_queue(req_id=req_id)
        except error.IBError as err:
            raise err

        print("Searching contracts with details from IB...")

        self.reqContractDetails(reqId=req_id, contract=contract)

        res: List[Union[ib_contract.ContractDetails, error.IBError]] = \
            await f_queue.get()

        if res:
            if f_queue.status is fq._Status.ERROR:
                if isinstance(res[-1], error.IBError):
                    raise res[-1]

            return res

        raise error.IBError(
            rid=req_id, err_code=error.IBErrorCode.RES_NO_CONTENT,
            err_str="Failed to get additional contract details"
        )

    async def resolve_head_timestamp(
            self, req_id: int, contract: ib_contract.Contract,
            show: Optional[dt.EarliestDataPoint] = dt.EarliestDataPoint.TRADES
        ) -> int:
        """Fetch the earliest available data point for a given instrument
        from IB.

        Args:
            req_id (int): Request ID (ticker ID in IB API).
            contract (:obj:`ibapi.contract.Contract`): `Contract` object with
                sufficient info to identify the instrument.
            show (Literal['BID', 'ASK', 'TRADES'], optional):
                Type of data for head timestamp. Defaults to 'TRADES'.

        Returns:
            int: Unix timestamp of the earliest available datapoint.

        Raises:
            ibpy_native.error.IBError: If
                - queue associated with `req_id` is being used by other tasks;
                - there's any error returned from IB;
                - no element found in received result;
                - multiple elements found in received result.
        """
        try:
            f_queue = self._wrapper.get_request_queue(req_id=req_id)
        except error.IBError as err:
            raise err

        print("Getting earliest available data point for the given "
              "instrument from IB... ")

        self.reqHeadTimeStamp(reqId=req_id, contract=contract,
                              whatToShow=show.value, useRTH=0, formatDate=2)

        res = await f_queue.get()

        # Cancel the head time stamp request to release the ID after the
        # request queue is finished
        self.cancelHeadTimeStamp(reqId=req_id)

        if res:
            if f_queue.status is fq._Status.ERROR:
                if isinstance(res[-1], error.IBError):
                    raise res[-1]

                raise self._unknown_error(req_id=req_id)

            if len(res) > 1:
                raise error.IBError(
                    rid=req_id, err_code=error.IBErrorCode.RES_UNEXPECTED,
                    err_str="[Abnormal] Multiple result received"
                )

            return int(res[0])

        raise error.IBError(
            rid=req_id, err_code=error.IBErrorCode.RES_NO_CONTENT,
            err_str="Failed to get the earliest available data point"
        )

    async def fetch_historical_ticks(
            self, req_id: int, contract: ib_contract.Contract,
            start: datetime.datetime,
            end: Optional[datetime.datetime] = datetime.datetime.now()\
                .astimezone(TZ),
            show: Optional[dt.HistoricalTicks] = dt.HistoricalTicks.TRADES
        ) -> dt.HistoricalTicksResult:
        """Fetch the historical ticks data for a given instrument from IB.

        Args:
            req_id (int): Request ID (ticker ID in IB API).
            contract (:obj:`ibapi.contract.Contract`): `Contract` object with
                sufficient info to identify the instrument.
            start (:obj:`datetime.datetime`): The time for the earliest tick
                data to be included.
            end (:obj:`datetime.datetime`, optional): The time for the latest
                tick data to be included. Defaults to now.
            show (Literal['MIDPOINT', 'BID_ASK', 'TRADES'], optional):
                Type of data requested. Defaults to 'TRADES'.

        Returns:
            Ticks data (fetched recursively to get around IB 1000 ticks limit)

        Raises:
            ValueError: If
                - `tzinfo` of `start` & `end` do not align;
                - Value of start` > `end`.
            ibpy_native.error.IBError: If
                - queue associated with `req_id` is being used by other tasks;
                - there's any error returned from IB before any tick data is
                fetched successfully;
                - no result received from IB with no tick fetched in pervious
                request(s);
                - incorrect number of items (!= 2) found in the result received
                from IB with no tick fetched in pervious request(s).
        """
        # Pre-process & error checking
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
            f_queue = self._wrapper.get_request_queue(req_id=req_id)
        except error.IBError as err:
            raise err

        all_ticks: list = []

        real_start_time = _IBClient.TZ.localize(start) if start.tzinfo is None \
            else start

        next_end_time = _IBClient.TZ.localize(end) if end.tzinfo is None \
            else end

        finished = False

        print(f"Getting historical ticks data [{show}] for the given"
              " instrument from IB...")

        while not finished:
            self.reqHistoricalTicks(
                reqId=req_id, contract=contract, startDateTime="",
                endDateTime=next_end_time.strftime(const._IB.TIME_FMT),
                numberOfTicks=1000, whatToShow=show.value, useRth=0,
                ignoreSize=False, miscOptions=[]
            )

            res: List[List[Union[ib_wrapper.HistoricalTick,
                                 ib_wrapper.HistoricalTickBidAsk,
                                 ib_wrapper.HistoricalTickLast]],
                      bool] = await f_queue.get()

            if res and f_queue.status is fq._Status.ERROR:
                # Response received and internal queue reports error
                if isinstance(res[-1], error.IBError):
                    if all_ticks:
                        if res[-1].err_code == error.IBErrorCode\
                            .INVALID_CONTRACT:
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

                raise self._unknown_error(req_id=req_id, extra=next_end_time)

            if res:
                if len(res) != 2:
                    # The result should be a list that contains 2 items:
                    # [ticks: ListOfHistoricalTick(BidAsk/Last), done: bool]
                    if all_ticks:
                        print("Abnormal result received while fetching the "
                              f"remaining ticks: returning {len(all_ticks)} "
                              "ticks fetched")
                        break

                    raise error.IBError(
                        rid=req_id, err_code=error.IBErrorCode.RES_UNEXPECTED,
                        err_str="[Abnormal] Incorrect number of items "
                        f"received: {len(res)}"
                    )

                # Process the data
                processed_result = self._process_historical_ticks(
                    ticks=res[0],
                    start_time=real_start_time,
                    end_time=next_end_time
                )
                all_ticks.extend(processed_result['ticks'])
                next_end_time = processed_result['next_end_time']

                print(
                    f"{len(all_ticks)} ticks fetched ("
                    f"{len(processed_result['ticks'])} new ticks); Next end "
                    f"time - {next_end_time.strftime(const._IB.TIME_FMT)}"
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

                raise error.IBError(
                    rid=req_id, err_code=error.IBErrorCode.RES_NO_CONTENT,
                    err_str="Failed to get historical ticks data"
                )

        all_ticks.reverse()

        # return (all_ticks, finished)
        return {'ticks': all_ticks,
                'completed': finished}

    # Stream live tick data
    async def stream_live_ticks(
            self, req_id: int, contract: ib_contract.Contract,
            listener: listeners.LiveTicksListener,
            tick_type: Optional[dt.LiveTicks] = dt.LiveTicks.LAST
        ):
        """Request to stream live tick data.

        Args:
            req_id (int): Request ID (ticker ID in IB API).
            contract (:obj:`ibapi.contract.Contract`): `Contract` object with
                sufficient info to identify the instrument.
            listener (:obj:`ibpy_native.interfaces.listeners.LiveTicksListener`):
                Callback listener for receiving ticks, finish signal, and error
                from IB API.
            tick_type (Literal['Last', 'AllLast', 'BidAsk', 'MidPoint'],
                optional): Type of tick to be requested. Defaults to 'Last'.

        Raises:
            ibpy_native.error.IBError: If queue associated with `req_id` is
                being used by other tasks.

        Note:
            The value `ibpy_native.utils.datatype.LiveTicks.ALL_LAST` of
            argument `tick_type` has additional trade types such as combos,
            derivatives, and average price trades which are not included in
            `ibpy_native.utils.datatype.LiveTicks.LAST`.
            Also, this function depends on `live_ticks_listener` to return
            live ticks received. The listener should be set explicitly.
        """
        try:
            f_queue = self._wrapper.get_request_queue(req_id)
        except error.IBError as err:
            raise err

        print(f"Streaming live ticks [{tick_type}] for the given instrument "
              "instrument from IB...")

        self.reqTickByTickData(
            reqId=req_id, contract=contract, tickType=tick_type.value,
            numberOfTicks=0, ignoreSize=True
        )

        async for elm in f_queue.stream():
            if isinstance(elm, (ib_wrapper.HistoricalTick,
                                ib_wrapper.HistoricalTickLast,
                                ib_wrapper.HistoricalTickBidAsk)):
                listener.on_tick_receive(req_id=req_id, tick=elm)
            elif isinstance(elm, error.IBError):
                listener.on_err(err=elm)
            elif elm is fq._Status.FINISHED:
                listener.on_finish(req_id=req_id)

    def cancel_live_ticks_stream(self, req_id: int):
        """Stop the live tick data stream that's currently streaming.

        Args:
            req_id (int): Request ID (ticker ID in IB API).

        Raises:
            ibpy_native.error.IBError: If there's no `_FinishableQueue` object
                associated with the specified `req_id` found in the internal
                `_IBWrapper` object.
        """
        f_queue = self._wrapper.get_request_queue_no_throw(req_id=req_id)

        if f_queue is not None:
            self.cancelTickByTickData(reqId=req_id)
            f_queue.put(element=fq._Status.FINISHED)
        else:
            raise error.IBError(
                rid=req_id, err_code=error.IBErrorCode.RES_NOT_FOUND,
                err_str=f"Task associated with request ID {req_id} not found"
            )

    # Private functions
    def _process_historical_ticks(
            self, ticks: List[Union[ib_wrapper.HistoricalTick,
                                    ib_wrapper.HistoricalTickBidAsk,
                                    ib_wrapper.HistoricalTickLast]],
            start_time: datetime.datetime,
            end_time: datetime.datetime
    ) -> _ProcessHistoricalTicksResult:
        """Processes the tick data returned from IB in function
        `fetch_historical_ticks`.
        """
        if ticks:
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
                end_time = datetime.datetime.fromtimestamp(ticks[-1].time)\
                    .astimezone(end_time.tzinfo)
            else:
                # Ticks data received from IB but all records included in
                # response are earlier than the start time.
                ticks = []
                end_time = start_time
        else:
            # Floor the `end_time` to pervious 30 minutes point to avoid IB
            # cutting off the data at the date start point for the instrument.
            # e.g.
            delta = datetime.timedelta(minutes=end_time.minute % 30,
                                       seconds=end_time.second)

            if delta.total_seconds() == 0:
                end_time = end_time - datetime.timedelta(minutes=30)
            else:
                end_time = end_time - delta

        return {'ticks': ticks,
                'next_end_time': end_time}

    def _unknown_error(self, req_id: int, extra: Any = None):
        """Constructs `IBError` with error code `UNKNOWN`

        For siturations which internal `_FinishableQueue` reports error status
        but not exception received.

        Args:
            req_id (int): Request ID (ticker ID in IB API).
            extra (:obj:`Any`, optional): Extra data to be passed through the
                exception. Defaults to `None`.

        Returns:
            ibpy_native.error.IBError: Preconfigured `IBError` object with
                error code `50500: UNKNOWN`
        """
        return error.IBError(
            rid=req_id, err_code=error.IBErrorCode.UNKNOWN,
            err_str="Unknown error: Internal queue reported error "
            "status but no exception received",
            err_extra=extra
        )
