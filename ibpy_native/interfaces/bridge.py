"""Interface module for `IBBridge`."""
import abc
import datetime
from typing import AsyncIterator, List, Optional

from ibapi import contract as ib_contract
from ibapi import order as ib_order

from ibpy_native import models
from ibpy_native.interfaces import delegates
from ibpy_native.interfaces import listeners
from ibpy_native.utils import datatype

class IBridge(metaclass=abc.ABCMeta):
    # pylint: disable=too-many-public-methods
    """Public interface of the class that bridge between `ibpy-native` & IB API.

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
            related data. Defaults to `None`.
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
    """
    @abc.abstractmethod
    def __init__(
        self, host: str="127.0.0.1", port: int=4001,
        client_id: int=1, auto_conn: bool=True,
        accounts_manager: Optional[delegates.AccountsManagementDelegate]=None,
        connection_listener: Optional[listeners.ConnectionListener]=None,
        notification_listener: Optional[listeners.NotificationListener]=None,
        order_events_listener: Optional[listeners.OrderEventsListener]=None
    ):
        pass

    #region - Properties
    @property
    @abc.abstractmethod
    def host(self) -> str:
        """str: Hostname / IP address of the TWS / IB Gateway instance
        connecting to.
        """
        return NotImplemented

    @property
    @abc.abstractmethod
    def port(self) -> int:
        """int: Socket port of this instance connecting to."""
        return NotImplemented

    @property
    @abc.abstractmethod
    def client_id(self) -> int:
        """int: Client ID specified for this instance."""
        return NotImplemented

    @property
    @abc.abstractmethod
    def is_connected(self) -> bool:
        """Check if the bridge is connected to a running & logged in TWS/IB
        Gateway instance.
        """
        return NotImplemented

    @property
    @abc.abstractmethod
    def orders_manager(self) -> delegates.OrdersManagementDelegate:
        """:obj:`ibpy_native.interfaces.delegates.OrdersManagementDelegate`:
        `ibpy_native.manager.OrdersManager` instance that handles order related
        events.
        """
        return NotImplemented
    #endregion - Properties

    @abc.abstractmethod
    def set_timezone(self, tz: datetime.tzinfo):
        # pylint: disable=invalid-name
        """Set the timezone for the bridge to match the IB Gateway/TWS timezone
        specified at login.

        Args:
            tz (datetime.tzinfo): Timezone. Recommend to set this value via
                `pytz.timezone(zone: str)`.
        """
        return NotImplemented

    @abc.abstractmethod
    def set_on_notify_listener(self, listener: listeners.NotificationListener):
        """Setter for optional `NotificationListener`.

        Args:
            listener (:obj:`ibpy_native.interfaces.listeners
                .NotificationListener`): Listener for IB notifications.
        """
        return NotImplemented

    #region - Connections
    @abc.abstractmethod
    def connect(self):
        """Connect the bridge to a running & logged in TWS/IB Gateway instance.
        """
        return NotImplemented

    @abc.abstractmethod
    def disconnect(self):
        """Disconnect the bridge from the connected TWS/IB Gateway instance.
        """
        return NotImplemented
    #endregion - Connections

    #region - IB account related
    @abc.abstractmethod
    def req_managed_accounts(self):
        """Fetch the accounts handle by the username logged in on IB Gateway."""
        return NotImplemented

    @abc.abstractmethod
    async def sub_account_updates(self, account: models.Account):
        """Subscribes to account updates from IB.

        Args:
            account (:obj:`ibpy_native.models.Account`): Account object
                retrieved from `AccountsManager`.
        """
        return NotImplemented

    @abc.abstractmethod
    async def unsub_account_updates(self,
                                    account: Optional[models.Account]=None):
        """Stop receiving account updates from IB.

        Args:
            account (:obj:`ibpy_native.models.Account`, optional):
                Account that's currently subscribed for account updates.
        """
        return NotImplemented
    #endregion - IB account related

    @abc.abstractmethod
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
        """
        return NotImplemented

    #region - Orders
    @abc.abstractmethod
    async def next_order_id(self) -> int:
        """Get next valid order ID.

        Returns:
            int: The next valid order ID.
        """
        return NotImplemented

    @abc.abstractmethod
    async def req_open_orders(self):
        """Get all active orders submitted by the client application connected
        with the exact same client ID with which the orders were sent to
        TWS/Gateway.
        """
        return NotImplemented

    @abc.abstractmethod
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
        """
        return NotImplemented

    @abc.abstractmethod
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
        return NotImplemented
    #endregion - Orders

    #region - Historical data
    @abc.abstractmethod
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
        """
        return NotImplemented

    @abc.abstractmethod
    async def req_historical_ticks(
        self, contract: ib_contract.Contract,
        start: Optional[datetime.datetime]=None,
        end: Optional[datetime.datetime]=None,
        tick_type: datatype.HistoricalTicks=datatype.HistoricalTicks.TRADES,
        daily_data_starting_point: Optional[datetime.time]=None,
        retry: int=0
    ) -> AsyncIterator[datatype.ResHistoricalTicks]:
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
        """
        return NotImplemented
    #endregion - Historical data

    #region - Live data
    @abc.abstractmethod
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
        return NotImplemented

    @abc.abstractmethod
    def stop_live_ticks_stream(self, stream_id: int):
        """Stop the specificed live tick data stream that's currently streaming.

        Args:
            stream_id (int): Identifier for the stream.
        """
        return NotImplemented
