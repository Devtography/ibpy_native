"""Code implementation of IB API resposes handling."""
# pylint: disable=protected-access
import queue
from typing import Dict, List, Optional, Union

from ibapi import contract as ib_contract
from ibapi import wrapper

from ibpy_native import error
from ibpy_native import models
from ibpy_native.interfaces import delegates
from ibpy_native.interfaces import listeners
from ibpy_native.utils import finishable_queue as fq

class _IBWrapper(wrapper.EWrapper):
    """The wrapper deals with the action coming back from the IB gateway or
    TWS instance.

    Args:
        notification_listener (:obj:`ibpy_native.interfaces.listeners
            .NotificationListener`, optional): Handler to receive system
            notifications from IB Gateway. Defaults to `None`.
    """
    def __init__(
        self,
        notification_listener: Optional[listeners.NotificationListener]=None
    ):
        self._req_queue: Dict[int, fq.FinishableQueue] = {}

        self._ac_man_delegate: Optional[
            delegates._AccountManagementDelegate] = None

        self._notification_listener: Optional[
                listeners.NotificationListener] = notification_listener

        super().__init__()

    @property
    def next_req_id(self) -> int:
        """The next usable request ID (ticker ID in IB API).

        Finds the next available request ID by looking up if there's any
        finished `FinishableQueue` in internal queue dictionary `__req_queue`.
        If so, returns the ID of the first finished `FinishableQueue` found.
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

    #region - Getters
    def get_request_queue(self, req_id: int) -> fq.FinishableQueue:
        """Initialise queue or returns the existing queue with ID `req_id`.

        Args:
            req_id (int): Request ID (ticker ID in IB API) to associate to the
                queue.

        Returns:
            :obj:`ibpy_native.utils.finishable_queue.FinishableQueue`:
                The newly initialised queue or the already existed queue
                associated to the `req_id`.

        Raises:
            ibpy_native.error.IBError: If `FinishableQueue` associated with
                `req_id` is being used by other tasks.
        """
        try:
            self.__init_req_queue(req_id=req_id)
        except error.IBError as err:
            raise err

        return self._req_queue[req_id]

    def get_request_queue_no_throw(self, req_id: int) -> Optional[
        fq.FinishableQueue
    ]:
        """Returns the existing queue with ID `req_id`.

        Args:
            req_id (int): Request ID (ticker ID in IB API) associated to the
                queue.

        Returns:
            :obj:`Optional[ibpy_native.utils.finishable_queue.FinishableQueue]`:
                The existing `FinishableQueue` associated to the specified
                `req_id`. `None` if `req_id` doesn't match with any existing
                `FinishableQueue` object.
        """
        return self._req_queue[req_id] if req_id in self._req_queue else None
    #endregion - Getters

    #region - Setters
    def set_account_management_delegate(
        self, delegate: delegates._AccountManagementDelegate
    ):
        """Setter for optional `_AccountListDelegate`.

        Args:
            delegate (ibpy_native.interfaces.delegates._AccountListDelegate):
                Delegate for managing IB account list.
        """
        self._ac_man_delegate = delegate

    def set_on_notify_listener(self, listener: listeners.NotificationListener):
        """Setter for optional `NotificationListener`.

        Args:
            listener (:obj:`ibpy_native.interfaces.listeners
                .NotificationListener`): Listener for IB notifications.
        """
        self._notification_listener = listener
    #endregion - Setters

    #region - Override functions from `wrapper.EWrapper`
    # Error handling
    def error(self, reqId, errorCode, errorString):
        err = error.IBError(rid=reqId, err_code=errorCode, err_str=errorString)

        # -1 indicates a notification and not true error condition
        if reqId is not -1:
            self._req_queue[reqId].put(element=err)
        else:
            if self._notification_listener is not None:
                self._notification_listener.on_notify(
                    msg_code=errorCode,
                    msg=errorString
                )

    #region - Accounts & portfolio
    def managedAccounts(self, accountsList: str):
        # Trim the spaces in `accountsList` received
        trimmed = "".join(accountsList.split())
        # Separate different account IDs into a list
        account_list = trimmed.split(",")

        if self._ac_man_delegate is not None:
            self._ac_man_delegate.on_account_list_update(
                account_list=account_list
            )

    #region - account updates
    def updateAccountValue(self, key: str, val: str, currency: str,
                           accountName: str):
        if self._ac_man_delegate:
            data = models.RawAccountValueData(
                account=accountName, currency=currency, key=key, val=val
            )
            self._ac_man_delegate.account_updates_queue.put(data)

    def updatePortfolio(self, contract: ib_contract.Contract, position: float,
                        marketPrice: float, marketValue: float,
                        averageCost: float, unrealizedPNL: float,
                        realizedPNL: float, accountName: str):
        if self._ac_man_delegate:
            data = models.RawPortfolioData(
                account=accountName, contract=contract,
                position=position, market_price=marketPrice,
                market_val=marketValue, avg_cost=averageCost,
                unrealised_pnl=unrealizedPNL, realised_pnl=realizedPNL
            )
            self._ac_man_delegate.account_updates_queue.put(data)

    def updateAccountTime(self, timeStamp: str):
        if self._ac_man_delegate:
            self._ac_man_delegate.account_updates_queue.put(timeStamp)
    #endregion - account updates
    #endregion - Accounts & portfolio

    #region - Get contract details
    def contractDetails(self, reqId, contractDetails):
        self._req_queue[reqId].put(element=contractDetails)

    def contractDetailsEnd(self, reqId):
        self._req_queue[reqId].put(element=fq.Status.FINISHED)
    #endregion - Get contract details

    # Get earliest data point for a given instrument and data
    def headTimestamp(self, reqId: int, headTimestamp: str):
        # override method
        self._req_queue[reqId].put(element=headTimestamp)
        self._req_queue[reqId].put(element=fq.Status.FINISHED)

    #region - Fetch historical tick data
    def historicalTicks(self, reqId: int,
                        ticks: List[wrapper.HistoricalTick], done: bool):
        self._handle_historical_ticks_results(reqId, ticks, done)

    def historicalTicksBidAsk(self, reqId: int,
                              ticks: List[wrapper.HistoricalTickBidAsk],
                              done: bool):
        self._handle_historical_ticks_results(req_id=reqId, ticks=ticks,
                                              done=done)

    def historicalTicksLast(self, reqId: int,
                            ticks: List[wrapper.HistoricalTickLast],
                            done: bool):
        self._handle_historical_ticks_results(req_id=reqId, ticks=ticks,
                                              done=done)
    #endregion - Fetch historical tick data

    #region - Stream live tick data
    def tickByTickAllLast(self, reqId: int, tickType: int, time: int,
                          price: float, size: int,
                          tickAttribLast: wrapper.TickAttribLast,
                          exchange: str, specialConditions: str):
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
        record = wrapper.HistoricalTickBidAsk()
        record.time = time
        record.priceBid = bidPrice
        record.sizeBid = bidSize
        record.priceAsk = askPrice
        record.sizeAsk = askSize
        record.tickAttribBidAsk = tickAttribBidAsk

        self._handle_live_ticks(req_id=reqId, tick=record)

    def tickByTickMidPoint(self, reqId: int, time: int, midPoint: float):
        record = wrapper.HistoricalTick()
        record.time = time
        record.price = midPoint

        self._handle_live_ticks(req_id=reqId, tick=record)
    #endregion - Stream live tick data
    #endregion - Override functions from `wrapper.EWrapper`

    #region - Private functions
    def __init_req_queue(self, req_id: int):
        """Initials a new `FinishableQueue` if there's no object at
        `self.__req_queue[req_id]`; Resets the queue status to its' initial
        status.

        Raises:
            ibpy_native.error.IBError: If a `FinishableQueue` already exists at
                `self.__req_queue[req_id]` and it's not finished.
        """
        if req_id in self._req_queue:
            if self._req_queue[req_id].finished:
                self._req_queue[req_id].reset()
            else:
                raise error.IBError(
                    rid=req_id, err_code=error.IBErrorCode.QUEUE_IN_USE,
                    err_str=f"Requested queue with ID {str(req_id)} is "
                            "currently in use"
                )
        else:
            self._req_queue[req_id] = fq.FinishableQueue(queue.Queue())

    def _handle_historical_ticks_results(
        self, req_id: int,
        ticks: Union[List[wrapper.HistoricalTick],
                     List[wrapper.HistoricalTickBidAsk],
                     List[wrapper.HistoricalTickLast],],
        done: bool
    ):
        """Handles results return from functions `historicalTicks`,
        `historicalTicksBidAsk`, and `historicalTicksLast` by putting the
        results into corresponding queue & marks the queue as finished.
        """
        self._req_queue[req_id].put(element=ticks)
        self._req_queue[req_id].put(element=done)
        self._req_queue[req_id].put(element=fq.Status.FINISHED)

    def _handle_live_ticks(self, req_id: int,
                           tick: Union[wrapper.HistoricalTick,
                                       wrapper.HistoricalTickBidAsk,
                                       wrapper.HistoricalTickLast,]):
        """Handles live ticks passed to functions `tickByTickAllLast`,
        `tickByTickBidAsk`, and `tickByTickMidPoint` by putting the ticks
        received into corresponding queue.
        """
        self._req_queue[req_id].put(element=tick)
    #endregion - Private functions
