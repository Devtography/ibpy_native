"""Code implementation of public interface to bridge between the package &
IB API.
"""
# pylint: disable=protected-access
import asyncio
import datetime
import time
import threading
from typing import AsyncIterator, Awaitable, List, Optional

from ibapi import contract as ib_contract
from ibapi import order as ib_order

from ibpy_native import error
from ibpy_native import interfaces
from ibpy_native import manager
from ibpy_native import models
from ibpy_native._internal import _client
from ibpy_native._internal import _global
from ibpy_native._internal import _wrapper
from ibpy_native.interfaces import delegates
from ibpy_native.interfaces import listeners
from ibpy_native.utils import datatype

class IBBridge(interfaces.IBridge):
    # pylint: disable=too-many-public-methods
    """Public class to bridge between `ibpy-native` & IB API.

    Args:
        host (str, optional): Hostname/IP address of IB Gateway. Defaults to
            `127.0.0.1`.
        port (int, optional): Port to connect to IB Gateway. Defaults to `4001`.
        client_id (int, optional): Session ID which will be shown on IB Gateway
            interface as `Client {client_id}`. Defaults to `1`.
        auto_conn (bool, optional): `IBBridge` auto connects to IB Gateway on
            initial. Defaults to `True`.
        accounts_manager (:obj:`ibpy_native.interfaces.delegates
            .AccountsManagementDelegate`, optional): Manager to handle accounts
            related data. If omitted, an default `AccountManager` will be
            created on initial of `IBBridge` (which should be enough for most
            cases unless you have a customised one). Defaults to `None`.
        connection_listener (:obj:`ibpy_native.interfaces.listeners
            .ConnectionListener`, optional): Listener to receive connection
            status callback on connection with IB TWS/Gateway is established or
            dropped. Defaults to `None`.
        notification_listener (:obj:`ibpy_native.internfaces.listeners
            .NotificationListener`, optional): Listener to receive system
            notifications from IB Gateway. Defaults to `None`.
        order_events_listener (:obj:`ibpy_native.interfaces.listeners
            .OrderEventsListener`, optional): Listener for order events.
            Defaults to `None`.

    Raises:
        ValueError: If value of argument `client_id` is greater than 9999.
    """
    def __init__(
        self, host: str="127.0.0.1", port: int=4001,
        client_id: int=1, auto_conn: bool=True,
        accounts_manager: Optional[delegates.AccountsManagementDelegate]=None,
        connection_listener: Optional[listeners.ConnectionListener]=None,
        notification_listener: Optional[listeners.NotificationListener]=None,
        order_events_listener: Optional[listeners.OrderEventsListener]=None
    ):
        super().__init__()

        if client_id > 9999:
            raise ValueError(f"Invalid client ID ({client_id} > 9999)")

        self._host = host
        self._port = port
        self._client_id = client_id
        self._accounts_manager = (
            manager.AccountsManager() if accounts_manager is None
            else accounts_manager
        )
        self._orders_manager = manager.OrdersManager(
            event_listener=order_events_listener)

        self._wrapper = _wrapper.IBWrapper(
            client_id=client_id,
            accounts_manager=self._accounts_manager,
            orders_manager=self._orders_manager,
            connection_listener=connection_listener,
            notification_listener=notification_listener
        )

        self._client = _client.IBClient(wrapper=self._wrapper)

        if auto_conn:
            self.connect()

    #region - Properties
    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def client_id(self) -> int:
        return self._client_id

    @property
    def is_connected(self) -> bool:
        """Check if the bridge is connected to a running & logged in TWS/IB
        Gateway instance.
        """
        return self._client.isConnected()

    @property
    def accounts_manager(self) -> delegates.AccountsManagementDelegate:
        """:obj:`ibpy_native.interfaces.delegates.AccountsManagementDelegate`:
        `ibpy_native.manager.AccountsManager` instance that stores & manages
        all IB account(s) related data.
        """
        return self._accounts_manager

    @property
    def orders_manager(self) -> delegates.OrdersManagementDelegate:
        """:obj:`ibpy_native.interfaces.delegates.OrdersManagementDelegate`:
        `ibpy_native.manager.OrdersManager` instance that handles order related
        events.
        """
        return self._orders_manager
    #endregion - Properties

    #region - Setters
    def set_timezone(self, tz: datetime.tzinfo):
        # pylint: disable=invalid-name
        """Set the timezone for the bridge to match the IB Gateway/TWS timezone
        specified at login.

        Note:
            Default timezone `America/New_York` will be used if this function
            has never been called.

        Args:
            tz (datetime.tzinfo): Timezone. Recommend to set this value via
                `pytz.timezone(zone: str)`.
        """
        _global.TZ = tz

    def set_on_notify_listener(self, listener: listeners.NotificationListener):
        """Setter for optional `NotificationListener`.

        Args:
            listener (:obj:`ibpy_native.interfaces.listeners
                .NotificationListener`): Listener for IB notifications.
        """
        self._wrapper.set_on_notify_listener(listener=listener)
    #endregion - Setters

    #region - Connections
    def connect(self):
        """Connect the bridge to a running & logged in TWS/IB Gateway instance.
        """
        if not self.is_connected:
            self._client.connect(host=self._host, port=self._port,
                                 clientId=self._client_id)

            threading.Thread(name="ib_loop", target=self._client.run).start()
            threading.Thread(name="heart_beat", target=self._heart_beat).start()

    def disconnect(self):
        """Disconnect the bridge from the connected TWS/IB Gateway instance.
        """
        self._client.disconnect()
    #endregion - Connections

    #region - IB account related
    def req_managed_accounts(self):
        """Fetch the accounts handle by the username logged in on IB Gateway."""
        self._client.reqManagedAccts()

    async def sub_account_updates(self, account: models.Account):
        """Subscribes to account updates from IB.

        Args:
            account (:obj:`ibpy_native.models.Account`): Account object
                retrieved from `AccountsManager`.
        """
        asyncio.create_task(
            self._accounts_manager.sub_account_updates(account=account)
        )
        self._client.reqAccountUpdates(subscribe=True,
                                       acctCode=account.account_id)

    async def unsub_account_updates(self,
                                    account: Optional[models.Account]=None):
        """Stop receiving account updates from IB.

        Args:
            account (:obj:`ibpy_native.models.Account`, optional):
                Account that's currently subscribed for account updates.
        """
        self._client.reqAccountUpdates(
            subscribe=False,
            acctCode="" if account is None else account.account_id
        )
        await self._accounts_manager.unsub_account_updates()
    #endregion - IB account related

    # Contracts
    async def search_detailed_contracts(
        self, contract: ib_contract.Contract
    ) -> List[ib_contract.ContractDetails]:
        """Search the contracts with complete details from IB's database.

        Args:
            contract (:obj:`ibapi.contract.Contract`): `Contract` object with
                partially completed info (e.g. symbol, currency, etc...)

        Returns:
            :obj:`List[ibapi.contract.ContractDetails]`: Fully fledged IB
                contract(s) with detailed info.

        Raises:
            ibpy_native.error.IBError: If
                - no result is found with the contract provided;
                - there's any error returned from IB.
        """
        try:
            res: List[ib_contract.ContractDetails] = (
                await self._client.resolve_contracts(
                    req_id=self._wrapper.next_req_id, contract=contract
                )
            )
        except error.IBError as err:
            raise err

        return  res

    #region - Orders
    async def next_order_id(self) -> int:
        """Get next valid order ID.

        Returns:
            int: The next valid order ID.
        """
        return await self._client.req_next_order_id()

    async def req_open_orders(self):
        """Get all active orders submitted by the client application connected
        with the exact same client ID with which the orders were sent to
        TWS/Gateway.

        Raises:
            ibpy_native.error.IBError: If the connection is dropped while
                waiting the request to finish.
        """
        try:
            await self._client.req_open_orders()
        except error.IBError as err:
            raise err

    async def place_orders(self, contract: ib_contract.Contract,
                           orders: List[ib_order.Order]):
        """Place order(s) to IB.

        Note:
            Order IDs must be unique for each order. Arguments `orders` can be
            used to place child order(s) together with the parent order but you
            should make sure orders passing in are all valid. All of the orders
            passed in will be cancelled if there's error casuse by any of the
            order in the list.

        Args:
            contract (:obj:`ibapi.contract.Contract`): The order's contract.
            orders (:obj:`List[ibapi.order.Order]`): Order(s) to be submitted.

        Raises:
            ibpy_native.error.IBError: If any order error returned from IB or
                lower level internal processes.
        """
        coroutines: List[Awaitable[None]] = []

        for order in orders:
            coroutines.append(self._client.submit_order(contract, order))

        try:
            await asyncio.gather(*coroutines)
        except error.IBError as err:
            for order in orders:
                self._client.cancel_order(order_id=order.orderId)

            raise err

    def cancel_order(self, order_id: int):
        """Cancel a submitted order.

        Note:
            No error will be raise even if you pass in an ID which doesn't
            match any existing open order. A warning message will be returned
            via the `NotificationListener` supplied instead.

            A message will be returned to the `NotificationListener` supplied
            once the order is cancelled.

        Args:
            order_id (int): The order's identifier.
        """
        self._client.cancel_order(order_id)
    #endregion - Orders

    #region - Historical data
    async def get_earliest_data_point(
        self, contract: ib_contract.Contract,
        data_type: datatype.EarliestDataPoint=datatype.EarliestDataPoint.TRADES
    ) -> datetime.datetime:
        """Returns the earliest data point of specified contract.

        Args:
            contract (:obj:`ibapi.contract.Contract`): `Contract` object with
                sufficient info to identify the instrument.
            data_type (:obj:`ibpy_native.utils.datatype.EarliestPoint`,
                optional): Type of data for earliest data point. Defaults to
                `EarliestPoint.TRADES`.

        Returns:
            :obj:`datetime.datetime`: The earliest data point for the specified
                contract in the timezone of whatever timezone set for this
                `IBBridge` instance.

        Raises:
            ibpy_native.error.IBError: If there is either connection related
                issue, IB returns 0 or multiple results.
        """
        try:
            result = await self._client.resolve_head_timestamp(
                req_id=self._wrapper.next_req_id, contract=contract,
                show=data_type
            )
        except error.IBError as err:
            raise err

        data_point = datetime.datetime.fromtimestamp(
            timestamp=result, tz=_global.TZ)

        return data_point.replace(tzinfo=None)

    async def req_historical_ticks(
        self, contract: ib_contract.Contract,
        start: Optional[datetime.datetime]=None,
        end: Optional[datetime.datetime]=None,
        tick_type: datatype.HistoricalTicks=datatype.HistoricalTicks.TRADES,
        daily_data_starting_point: Optional[datetime.time]=None,
        retry: int=0
    ) -> AsyncIterator[datatype.ResHistoricalTicks]:
        # pylint: disable=too-many-statements
        """Retrieve historical tick data for specificed instrument/contract
        from IB.

        Args:
            contract (:obj:`ibapi.contract.Contract`): `Contract` object with
                sufficient info to identify the instrument.
            start (:obj:`datetime.datetime`, optional): Datetime for the
                earliest tick data to be included. If is `None`, the start time
                will be set as the earliest data point. Defaults to `None`.
            end (:obj:`datetime.datetime`, optional): Datetime for the latest
                tick data to be included. If is `None`, the end time will be
                set as now. Defaults to `None`.
            tick_type (:obj:`ibpy_native.utils.datatype.HistoricalTicks`,
                optional): Type of tick data. Defaults to
                `HistoricalTicks.TRADES`.
            daily_data_starting_point (:obj:`datetime.time`, optional): The
                starting time of the ticks for each trading day. Specified this
                value to reduce number of requests needed to go over day(s)
                with no tick. Defaults to `None`.
            retry (int): Max retry attempts if error occur before terminating
                the task and rasing the error.

        Yields:
            :obj:ibpy_native.utils.datatype.ResHistoricalTicks`: Tick data
                received from IB. Attribute `completed` indicates if all ticks
                within the specified time period are received.

        Raises:
            ValueError: If
                - either argument `start`, `end`, or is not an native
                `datetime` object;
                - `tzinfo` of `daily_data_starting_point` is not `None`.
            ibpy_native.error.IBError: If
                - `contract` passed in is unresolvable;
                - there is any issue raised from the request function while
                excuteing the task, and max retry attemps has been reached.
        """
        # Error checking
        if start is not None:
            if start.tzinfo is not None:
                raise ValueError("Value of argument `start` & `end` must be an "
                                 "native `datetime` object.")
        if end is not None:
            if end.tzinfo is not None:
                raise ValueError("Value of argument `start` & `end` must be an "
                                 "native `datetime` object.")

        if daily_data_starting_point is not None:
            if daily_data_starting_point.tzinfo is not None:
                raise ValueError("Value of argument `daily_data_starting_point`"
                                 " must not contain timezone info.")
        # Prep start and end time
        try:
            if tick_type is datatype.HistoricalTicks.TRADES:
                head_time = await self.get_earliest_data_point(contract)
            else:
                head_time_ask = await self.get_earliest_data_point(
                    contract, data_type=datatype.EarliestDataPoint.ASK)
                head_time_bid = await self.get_earliest_data_point(
                    contract, data_type=datatype.EarliestDataPoint.BID)
                head_time = (head_time_ask if head_time_ask < head_time_bid
                             else head_time_bid)
        except error.IBError as err:
            raise err

        start_date_time = (head_time if start is None or head_time > start
                           else start)
        end_date_time = (datetime.datetime.now()
                         .astimezone(_global.TZ)
                         .replace(tzinfo=None))

        if end is not None:
            if end < end_date_time:
                end_date_time = end

        # Request tick data
        finished = False
        retry_attemps = 0

        while not finished:
            try:
                ticks = await self._client.req_historical_ticks(
                    req_id=self._wrapper.next_req_id, contract=contract,
                    start_date_time=start_date_time, show=tick_type
                )
            except error.IBError as err:
                if err.err_code == error.IBErrorCode.NOT_CONNECTED.value:
                    raise err
                if retry_attemps < retry:
                    retry_attemps += 1
                    continue

                raise err

            retry_attemps = 0

            # pylint: disable=consider-using-enumerate
            # Use range as the index is needed to slice the list
            for i in range(len(ticks)):
                data_time = datetime.datetime.fromtimestamp(
                    timestamp=ticks[i].time, tz=_global.TZ
                ).replace(tzinfo=None)
                if data_time >= start_date_time:
                    # Slices the list to include ticks not earlier than
                    # the start time of this iteration.
                    ticks = ticks[i:]
                    break
                if i == len(ticks) - 1:
                    # Only 1 tick received and that record is earlier the
                    # requested start time.
                    ticks = []

            if ticks:
                # Determine if it should fetch next batch of data
                last_tick_time = datetime.datetime.fromtimestamp(
                    timestamp=ticks[-1].time, tz=_global.TZ
                ).replace(tzinfo=None)

                if last_tick_time >= end_date_time:
                    # All ticks within the specified time period are received
                    finished = True
                    start_date_time = None
                    for i in range(len(ticks) - 1, -1, -1):
                        data_time = datetime.datetime.fromtimestamp(
                            timestamp=ticks[i].time, tz=_global.TZ
                        ).replace(tzinfo=None)
                        if data_time > end_date_time:
                            del ticks[i]
                        else:
                            break
                else:
                    # Ready for next request
                    start_date_time = (last_tick_time +
                                       datetime.timedelta(seconds=1))
            else: # If no tick is returned
                start_date_time = self._advance_time(
                    time_to_advance=start_date_time,
                    reset_point=daily_data_starting_point
                )

            if start_date_time is not None:
                if (_global.TZ.localize(start_date_time)
                    >= datetime.datetime.now().astimezone(_global.TZ)
                    or start_date_time >= end_date_time):
                    # Indicates all ticks up until now are received
                    finished = True
                    start_date_time = None

            # Yield the result
            yield datatype.ResHistoricalTicks(
                ticks=ticks, completed=finished,
                next_start_time=start_date_time
            )
    #endregion - Historical data

    #region - Live data
    async def stream_live_ticks(
        self, contract: ib_contract.Contract,
        listener: listeners.LiveTicksListener,
        tick_type: datatype.LiveTicks=datatype.LiveTicks.LAST
    ) -> int:
        """Request to stream live tick data.

        Args:
            contract (:obj:`ibapi.contract.Contract`): `Contract` object with
                sufficient info to identify the instrument.
            listener (:obj:`ibpy_native.interfaces.listenersLiveTicksListener`):
                Callback listener for receiving ticks, finish signale, and
                error from IB API.
            tick_type (:obj:`ibpy_native.utils.datatype.LiveTicks`, optional):
                Type of ticks to be requested. Defaults to `LiveTicks.Last`.

        Returns:
            int: Request identifier. This will be needed to stop the stream
                started by this function.
        """
        req_id = self._wrapper.next_req_id

        asyncio.create_task(
            self._client.stream_live_ticks(
                req_id=req_id, contract=contract, listener=listener,
                tick_type=tick_type
            )
        )

        return req_id

    def stop_live_ticks_stream(self, stream_id: int):
        """Stop the specificed live tick data stream that's currently streaming.

        Args:
            stream_id (int): Identifier for the stream.

        Raises:
            ibpy_native.error.IBError: If the specificed identifier has no
                stream associated with.
        """
        try:
            self._client.cancel_live_ticks_stream(req_id=stream_id)
        except error.IBError as err:
            raise err
    #endregion - Live data

    #region - Private functions
    def _heart_beat(self):
        """Infinity loop to monitor connection with TWS/Gateway."""
        while True:
            time.sleep(2)
            if not self._client.isConnected():
                break
            self._client.reqCurrentTime()

    def _advance_time(
        self, time_to_advance=datetime.datetime,
        reset_point: Optional[datetime.time] = None
    ) -> datetime.datetime:
        """Advances the specificed time to either next 30 minutes point or the
        time specified in `reset_point`.
        """
        result = time_to_advance

        if reset_point is not None:
            if time_to_advance.time() >= reset_point:
                time_to_advance += datetime.timedelta(days=1)

            result = time_to_advance.replace(
                hour=reset_point.hour, minute=reset_point.minute,
                second=0, microsecond=0
            )
        else:
            delta = datetime.timedelta(minutes=time_to_advance.minute % 30,
                                       seconds=time_to_advance.second)
            if delta.total_seconds() == 0: # Plus 30 minutes
                result = time_to_advance + datetime.timedelta(minutes=30)
            else: # Rounds up to next 30 minutes point
                result = (
                        time_to_advance + (datetime.datetime.min -
                        time_to_advance) % datetime.timedelta(minutes=30)
                )

        return result

    #endregion - Private functions
