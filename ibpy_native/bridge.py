"""Code implementation of public interface to bridge between the package &
IB API.
"""
# pylint: disable=protected-access
import asyncio
import datetime
import threading
from typing import Iterator, List, Optional

from ibapi import contract as ib_contract

import ibpy_native
from ibpy_native import account as ib_account
from ibpy_native import error
from ibpy_native import models
from ibpy_native._internal import _client
from ibpy_native._internal import _global
from ibpy_native._internal import _wrapper
from ibpy_native.interfaces import delegates
from ibpy_native.interfaces import listeners
from ibpy_native.utils import datatype

class IBBridge:
    """Public class to bridge between `ibpy-native` & IB API.

    Args:
        host (str, optional): Hostname/IP address of IB Gateway. Defaults to
            `127.0.0.1`.
        port (int, optional): Port to connect to IB Gateway. Defaults to `4001`.
        client_id (int, optional): Session ID which will be shown on IB Gateway
            interface as `Client {client_id}`. Defaults to `1`.
        auto_conn (bool, optional): `IBBridge` auto connects to IB Gateway on
            initial. Defaults to `True`.
        notification_listener (:obj:`ibpy_native.internfaces.listeners
            .NotificationListener`, optional): Handler to receive system
            notifications from IB Gateway. Defaults to `None`.
        accounts_manager (:obj:`ibpy_native.account.AccountsManager`, optional):
            Object to handle accounts related data. If omitted, an default
            one will be created on initial of `IBBridge` (which should be
            enough for most cases unless you have a customised one). Defaults
            to `None`.
    """
    def __init__(
        self, host: str="127.0.0.1", port: int=4001,
        client_id: int=1, auto_conn: bool=True,
        notification_listener:Optional[listeners.NotificationListener]=None,
        accounts_manager: Optional[ib_account.AccountsManager]=None
    ):
        self._host = host
        self._port = port
        self._client_id = client_id
        self._accounts_manager = (
            ib_account.AccountsManager() if accounts_manager is None
            else accounts_manager
        )
        self._orders_manager = ibpy_native.OrdersManager()

        self._wrapper = _wrapper.IBWrapper(
            orders_manager=self._orders_manager,
            notification_listener=notification_listener
        )
        self._wrapper.set_accounts_management_delegate(
            delegate=self._accounts_manager
        )

        self._client = _client.IBClient(wrapper=self._wrapper)

        if auto_conn:
            self.connect()

    # Properties
    @property
    def is_connected(self) -> bool:
        """Check if the bridge is connected to a running & logged in TWS/IB
        Gateway instance.
        """
        return self._client.isConnected()

    @property
    def accounts_manager(self) -> ib_account.AccountsManager:
        """:obj:`ibpy_native.account.AccountsManager`: Instance that stores &
            manages all IB account(s) related data.
        """
        return self._accounts_manager

    @property
    def orders_manager(self) -> delegates.OrdersManagementDelegate:
        """:obj:`ibpy_native.order.OrdersManager`: Instance that handles order
        related events.
        """
        return self._orders_manager

    #region - Setters
    @staticmethod
    def set_timezone(tz: datetime.tzinfo):
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

            thread = threading.Thread(target=self._client.run)
            thread.start()

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

    async def unsub_account_updates(
        self, account: Optional[models.Account]=None
    ):
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

    #region - Historical data
    async def get_earliest_data_point(
        self, contract: ib_contract.Contract,
        data_type: datatype.EarliestDataPoint=datatype.EarliestDataPoint.TRADES
    ) -> datetime:
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
        retry: int=0
    ) -> Iterator[datatype.ResHistoricalTicks]:
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
            retry (int): Max retry attempts if error occur before terminating
                the task and rasing the error.

        Yields:
            :obj:ibpy_native.utils.datatype.ResHistoricalTicks`: Tick data
                received from IB. Attribute `completed` indicates if all ticks
                within the specified time period are received.

        Raises:
            ValueError: If either argument `start` or `end` is not an native
                `datetime` object;
            ibpy_native.error.IBError: If
                - `contract` passed in is unresolvable;
                - there is any issue raised from the request function while
                excuteing the task, and max retry attemps has been reached.
        """
        # Error checking
        if start.tzinfo is not None or end.tzinfo is not None:
            raise ValueError("Value of argument `start` & `end` must be an "
                             "native `datetime` object.")
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

        start_date_time = head_time if head_time > start else start
        end_date_time = datetime.datetime.now() if end is None else end

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
                if retry_attemps < retry:
                    continue
                raise err

            if ticks:
                # Drop the 1st tick as tick time of it is `start_date_time`
                # - 1 second
                del ticks[0]
                # Determine if it should fetch next batch of data
                last_tick_time = datetime.datetime.fromtimestamp(
                    timestamp=ticks[-1].time, tz=_global.TZ
                ).replace(tzinfo=None)

                if last_tick_time >= end_date_time:
                    # All ticks within the specified time period are received
                    finished = True
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
            # Yield the result
            yield datatype.ResHistoricalTicks(ticks=ticks, completed=finished)
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
