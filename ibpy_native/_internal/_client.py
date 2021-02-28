"""Code implementation for `EClient` related stuffs"""
# pylint: disable=protected-access
import datetime
from typing import Any, List, Union

from ibapi import client as ib_client
from ibapi import contract as ib_contract
from ibapi import order as ib_order
from ibapi import wrapper as ib_wrapper

from ibpy_native import error
from ibpy_native._internal import _global
from ibpy_native._internal import _typing
from ibpy_native._internal import _wrapper
from ibpy_native.interfaces import listeners
from ibpy_native.utils import datatype
from ibpy_native.utils import finishable_queue as fq

class IBClient(ib_client.EClient):
    """The client calls the native methods from IBWrapper instead of
    overriding native methods.

    Args:
        wrapper (:obj:`ibpy_native._internal._wrapper.IBWrapper`): The wrapper
            object to handle messages return from IB Gateway.
    """
    def __init__(self, wrapper: _wrapper.IBWrapper):
        self._wrapper = wrapper
        super().__init__(wrapper)

    #region - Contract
    async def resolve_contract(
        self, req_id: int, contract: ib_contract.Contract
    ) -> ib_contract.Contract:
        """From a partially formed contract, returns a fully fledged version.

        Args:
            req_id (int): Request ID (ticker ID in IB API).
            contract (:obj:`ibapi.contract.Contract`): `Contract` object with
                partially completed info (e.g. symbol, currency, etc...)

        Returns:
            :obj:`ibapi.contract.Contract`: Fully resolved IB contract.

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

        self.reqContractDetails(reqId=req_id, contract=contract)

        # Run until we get a valid contract(s)
        res = await f_queue.get()

        if res:
            if f_queue.status is fq.Status.ERROR:
                if isinstance(res[-1], error.IBError):
                    raise res[-1]

                raise self._unknown_error(req_id=req_id)

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
                partially completed info (e.g. symbol, currency, etc...)

        Returns:
            :obj:`list` of `ibapi.contract.ContractDetails`: Fully fledged IB
                contract(s) with detailed info.

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

        self.reqContractDetails(reqId=req_id, contract=contract)

        res: List[Union[ib_contract.ContractDetails, error.IBError]] = (
            await f_queue.get()
        )

        if res:
            if f_queue.status is fq.Status.ERROR:
                if isinstance(res[-1], error.IBError):
                    raise res[-1]

            return res

        raise error.IBError(
            rid=req_id, err_code=error.IBErrorCode.RES_NO_CONTENT,
            err_str="Failed to get additional contract details"
        )
    #endregion - Contract

    #region - Orders
    async def req_next_order_id(self) -> int:
        """Request the next valid order ID from IB.

        Returns:
            int: The next valid order ID returned from IB.

        Raises:
            ibpy_native.error.IBError: If queue associated with `req_id` -1 is
                being used by other task.
        """
        try:
            f_queue = self._wrapper.get_request_queue(
                req_id=_global.IDX_NEXT_ORDER_ID)
        except error.IBError as err:
            raise err
        # Request next valid order ID
        self.reqIds(numIds=-1) # `numIds` has deprecated
        await f_queue.get()

        return self._wrapper.orders_manager.next_order_id

    async def req_open_orders(self):
        """Request all active orders submitted by the client application
        connected with the exact same client ID with which the orders were sent
        to the TWS/Gateway.

        Raises:
            ibpy_native.error.IBError: If
                - queue destinated for the open orders requests is being used
                by other on-going task/request;
                - connection with IB TWS/Gateway is dropped while waiting for
                the task to finish.
        """
        try:
            queue = self._wrapper.get_request_queue(
                req_id=_global.IDX_OPEN_ORDERS)
        except error.IBError as err:
            raise err

        self.reqOpenOrders()
        result = await queue.get()
        if queue.status is fq.Status.ERROR:
            if isinstance(result[-1], error.IBError):
                raise result[-1]

    async def submit_order(self, contract: ib_contract.Contract,
                           order: ib_order.Order):
        """Send the order to IB TWS/Gateway for submission.

        Args:
            contract (:obj:`ibapi.contract.Contract`): The order's contract.
            order (:obj:`ibapi.order.Order`): Order to be submitted.

        Raises:
            ibpy_native.error.IBError: If
                - pending order with order ID same as the order passed in;
                - order error is returned from IB after the order is sent to
                TWS/Gateway.
        """
        try:
            self._wrapper.orders_manager.on_order_submission(
                order_id=order.orderId)
        except error.IBError as err:
            raise err
        self.placeOrder(orderId=order.orderId, contract=contract, order=order)

        queue = self._wrapper.orders_manager.get_pending_queue(
            order_id=order.orderId)
        result = await queue.get() # Wait for completeion signal

        if queue.status is fq.Status.ERROR:
            if isinstance(result[-1], error.IBError):
                raise result[-1]

    def cancel_order(self, order_id: int):
        """Cancel an order submitted.

        Args:
            order_id (int): The order's identifer.
        """
        self.cancelOrder(orderId=order_id)
        if self._wrapper.orders_manager.is_pending_order(order_id):
            # Send finish signal to the pending order
            queue = self._wrapper.orders_manager.get_pending_queue(order_id)
            if queue.status is not (fq.Status.FINISHED or fq.Status.ERROR):
                queue.put(element=fq.Status.FINISHED)
    #endregion - Orders

    #region - Historical data
    async def resolve_head_timestamp(
        self, req_id: int, contract: ib_contract.Contract,
        show: datatype.EarliestDataPoint=datatype.EarliestDataPoint.TRADES
    ) -> int:
        """Fetch the earliest available data point for a given instrument
        from IB.

        Args:
            req_id (int): Request ID (ticker ID in IB API).
            contract (:obj:`ibapi.contract.Contract`): `Contract` object with
                sufficient info to identify the instrument.
            show (:obj:`ibpy_native.utils.datatype.EarliestDataPoint`,
                optional): Type of data for head timestamp. Defaults to
                `EarliestDataPoint.TRADES`.

        Returns:
            int: Unix timestamp of the earliest available datapoint.

        Raises:
            ibpy_native.error.IBError: If
                - queue associated with `req_id` is being used by other tasks;
                - there's any error returned from IB;
        """
        try:
            f_queue = self._wrapper.get_request_queue(req_id=req_id)
        except error.IBError as err:
            raise err

        self.reqHeadTimeStamp(reqId=req_id, contract=contract,
                              whatToShow=show.value, useRTH=0, formatDate=2)

        res = await f_queue.get()

        # Cancel the head time stamp request to release the ID after the
        # request queue is finished
        self.cancelHeadTimeStamp(reqId=req_id)

        if res:
            if f_queue.status is fq.Status.ERROR:
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

    async def req_historical_ticks(
        self, req_id: int, contract: ib_contract.Contract,
        start_date_time: datetime.datetime,
        show: datatype.HistoricalTicks=datatype.HistoricalTicks.TRADES
    ) -> _typing.ResHistoricalTicks:
        """Request historical tick data of the given instrument from IB.

        Args:
            req_id (int): Request ID (ticker ID in IB API).
            contract (:obj:`ibapi.contract.Contract`): `Contract` object with
                sufficient info to identify the instrument.
            start_date_time (:obj:`datetime.datetime`): Time for the earliest
                tick data to be included.
            show (:obj:`ibpy_native.utils.datatype.HistoricalTicks`, optional):
                Type of data to be requested. Defaults to
                `HistoricalTicks.TRADES`.

        Returns:
            :obj:`ibpy_native._internal._typing.ResHistoricalTicks`: Tick data
                returned from IB.

        Raises:
            ValueError: If argument `start_date_time` is an aware `datetime`
                object.
            ibpy_native.error.IBError: If
                - queue associated with argument `req_id` is being used by other
                task;
                - there's any error returned from IB;
                - Data received from IB is indicated as incomplete.

        Notes:
            Around 1000 ticks will be returned from IB. Ticks returned will
            always cover a full second as describled in IB API document.
        """
        # Error checking
        if start_date_time.tzinfo is not None:
            raise ValueError("Value of argument `start_date_time` must not "
                             "be an aware `datetime` object.")
        # Pre-processing
        try:
            f_queue = self._wrapper.get_request_queue(req_id)
        except error.IBError as err:
            raise err

        converted_start_time = _global.TZ.localize(start_date_time)

        self.reqHistoricalTicks(
            reqId=req_id, contract=contract,
            startDateTime=converted_start_time.strftime(_global.TIME_FMT),
            endDateTime="", numberOfTicks=1000, whatToShow=show.value,
            useRth=0, ignoreSize=False, miscOptions=[]
        )

        result: _typing.WrapperResHistoricalTicks = await f_queue.get()

        if result:
            if f_queue.status is fq.Status.ERROR:
                # Handle error returned from IB
                if isinstance(result[-1], error.IBError):
                    raise result[-1]

            if not result[1]:
                raise error.IBError(
                    rid=req_id, err_code=error.IBErrorCode.RES_UNEXPECTED,
                    err_str="Not all historical tick data has been received "
                            "for this request. Please retry."
                )

            return result[0]
    #endregion - Historical data

    #region - Stream live tick data
    async def stream_live_ticks(
        self, req_id: int, contract: ib_contract.Contract,
        listener: listeners.LiveTicksListener,
        tick_type: datatype.LiveTicks=datatype.LiveTicks.LAST
    ):
        """Request to stream live tick data.

        Args:
            req_id (int): Request ID (ticker ID in IB API).
            contract (:obj:`ibapi.contract.Contract`): `Contract` object with
                sufficient info to identify the instrument.
            listener (:obj:`ibpy_native.interfaces.listeners
                .LiveTicksListener`): Callback listener for receiving ticks,
                finish signal, and error from IB API.
            tick_type (:obj:`ibpy_native.utils.datatype.LiveTicks`, optional):
                Type of tick to be requested. Defaults to `LiveTicks.LAST`.

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

        self.reqTickByTickData(
            reqId=req_id, contract=contract, tickType=tick_type.value,
            numberOfTicks=0, ignoreSize=True
        )

        async for elm in f_queue.stream():
            if isinstance(elm, (ib_wrapper.HistoricalTick,
                                ib_wrapper.HistoricalTickLast,
                                ib_wrapper.HistoricalTickBidAsk,)):
                listener.on_tick_receive(req_id=req_id, tick=elm)
            elif isinstance(elm, error.IBError):
                listener.on_err(err=elm)
            elif elm is fq.Status.FINISHED:
                listener.on_finish(req_id=req_id)

    def cancel_live_ticks_stream(self, req_id: int):
        """Stop the live tick data stream that's currently streaming.

        Args:
            req_id (int): Request ID (ticker ID in IB API).

        Raises:
            ibpy_native.error.IBError: If there's no `FinishableQueue` object
                associated with the specified `req_id` found in the internal
                `IBWrapper` object.
        """
        f_queue = self._wrapper.get_request_queue_no_throw(req_id=req_id)

        if f_queue is not None:
            self.cancelTickByTickData(reqId=req_id)
            f_queue.put(element=fq.Status.FINISHED)
        else:
            raise error.IBError(
                rid=req_id, err_code=error.IBErrorCode.RES_NOT_FOUND,
                err_str=f"Task associated with request ID {req_id} not found"
            )
    #endregion - Stream live tick data

    #region - Private functions
    def _unknown_error(self, req_id: int, extra: Any = None):
        """Constructs `IBError` with error code `UNKNOWN`

        For siturations which internal `FinishableQueue` reports error status
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
    #endregion - Private functions
