"""Code implementation of public interface to bridge between the package &
IB API.
"""
# pylint: disable=protected-access
import asyncio
import datetime
import threading
from typing import List, Optional

from ibapi import contract as ib_contract

from ibpy_native import account as ib_account
from ibpy_native import error
from ibpy_native import models
from ibpy_native._internal import _client as ib_client
from ibpy_native._internal import _wrapper as ib_wrapper
from ibpy_native.interfaces import listeners
from ibpy_native.utils import const
from ibpy_native.utils import datatype as dt

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

        self._wrapper = ib_wrapper.IBWrapper(
            notification_listener=notification_listener
        )
        self._wrapper.set_account_management_delegate(
            delegate=self._accounts_manager
        )

        self._client = ib_client.IBClient(wrapper=self._wrapper)

        if auto_conn:
            self.connect()

    # Properties
    @property
    def accounts_manager(self) -> ib_account.AccountsManager:
        """:obj:`ibpy_native.account.AccountsManager`: Instance that stores &
            manages all IB account(s) related data.
        """
        return self._accounts_manager

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
        ib_client.IBClient.TZ = tz

    def set_on_notify_listener(self, listener: listeners.NotificationListener):
        """Setter for optional `NotificationListener`.

        Args:
            listener (:obj:`ibpy_native.interfaces.listeners
                .NotificationListener`): Listener for IB notifications.
        """
        self._wrapper.set_on_notify_listener(listener=listener)
    #endregion - Setters

    #region - Connections
    def is_connected(self) -> bool:
        """Check if the bridge is connected to a running & logged in TWS/IB
        Gateway instance.
        """
        return self._client.isConnected()

    def connect(self):
        """Connect the bridge to a running & logged in TWS/IB Gateway instance.
        """
        if not self.is_connected():
            self._client.connect(host=self._host, port=self._port,
                                 clientId=self._client_id)

            thread = threading.Thread(target=self._client.run)
            thread.start()

            setattr(self._client, "_thread", thread)

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
        data_type: dt.EarliestDataPoint=dt.EarliestDataPoint.TRADES
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
            result
        ).astimezone(
            ib_client.IBClient.TZ
        )

        return data_point.replace(tzinfo=None)

    async def get_historical_ticks(
        self, contract: ib_contract.Contract, start: datetime.datetime=None,
        end: datetime.datetime=datetime.datetime.now(),
        data_type: dt.HistoricalTicks=dt.HistoricalTicks.TRADES,
        attempts: int=1
    ) -> dt.HistoricalTicksResult:
        """Retrieve historical ticks data for specificed instrument/contract
        from IB.

        Note:
            Multiple attempts is recommended for requesting long period of
            data as the request may timeout due to IB delays the responds to
            protect their service over a long session.
            Longer timeout value is also recommended for the same reason. Around
            30 to 100 seconds should be reasonable.

        Args:
            contract (:obj:`ibapi.contract.Contract`): `Contract` object with
                sufficient info to identify the instrument.
            start (:obj:`datetime.datetime`, optional): The time for the
                earliest tick data to be included. Defaults to `None`.
            end (:obj:`datetime.datetime`, optional): The time for the latest
                tick data to be included. Defaults to now.
            data_type (:obj:`ibpy_native.utils.datatype.HistoricalTicks`,
                optional): Type of data for the ticks. Defaults to
                `HistoricalTicks.TRADES`.
            attempts (int, optional): Attemp(s) to try requesting the historical
                ticks. Passing -1 into this argument will let the function
                retries for infinity times until all available ticks are received. Defaults to 1.

        Returns:
            :obj:`ibpy_native.utils.datatype.IBTicksResult`: Ticks returned
                from IB and a boolean to indicate if the returning object
                contains all available ticks.

        Raises:
            ValueError: If
                - argument `start` or `end` contains the timezone info;
                - timestamp of `start` is earlier than the earliest available
                datapoint.
                - timestamp of `end` is earlier than `start` or earliest
                available datapoint;
                - value of `attempts` < 1 and != -1.
            ibpy_native.error.IBError: If there is any issue raised from the
                request function while excuteing the task, with `attempts
                reduced to 0 and no tick fetched successfully in pervious
                attempt(s).
        """
        all_ticks = []
        next_end_time = ib_client.IBClient.TZ.localize(dt=end)

        # Error checking
        if end.tzinfo is not None or (start is not None and
                                      start.tzinfo is not None):
            raise ValueError(
                "Timezone should not be specified in either `start` or `end`."
            )

        try:
            head_timestamp = datetime.datetime.fromtimestamp(
                await self._client.resolve_head_timestamp(
                    req_id=self._wrapper.next_req_id, contract=contract,
                    show=dt.EarliestDataPoint.TRADES if (
                        data_type is dt.HistoricalTicks.TRADES
                     ) else dt.EarliestDataPoint.BID
                )
            ).astimezone(tz=ib_client.IBClient.TZ)
        except error.IBError as err:
            raise err

        if start is not None:
            if start.timestamp() < head_timestamp.timestamp():
                raise ValueError(
                    "Specificed start time is earlier than the earliest "
                    "available datapoint - "
                    f"{head_timestamp.strftime(const._IB.TIME_FMT)}"
                )
            if end.timestamp() < start.timestamp():
                raise ValueError(
                    "Specificed end time cannot be earlier than start time"
                )

            start = ib_client.IBClient.TZ.localize(dt=start)
        else:
            start = head_timestamp

        if next_end_time.timestamp() < head_timestamp.timestamp():
            raise ValueError(
                "Specificed end time is earlier than the earliest available "
                f"datapoint - {head_timestamp.strftime(const._IB.TIME_FMT)}"
            )

        if attempts < 1 and attempts != -1:
            raise ValueError(
                "Value of argument `attempts` must be positive integer or -1"
            )

        # Process the request
        while attempts > 0 or attempts == -1:
            attempts = attempts - 1 if attempts != -1 else attempts

            try:
                res = await self._client.fetch_historical_ticks(
                    req_id=self._wrapper.next_req_id, contract=contract,
                    start=start, end=next_end_time, show=data_type
                )

                #  `ticks[1]` is a boolean represents if the data are all
                # fetched without timeout
                if res["completed"]:
                    res["ticks"].extend(all_ticks)

                    return {
                        "ticks": res["ticks"],
                        "completed": True,
                    }

                res["ticks"].extend(all_ticks)
                all_ticks = res["ticks"]

                next_end_time = datetime.datetime.fromtimestamp(
                    res[0][0].time
                ).astimezone(ib_client.IBClient.TZ)
            except ValueError as err:
                raise err
            except error.IBError as err:
                if err.err_code == error.IBErrorCode.DUPLICATE_TICKER_ID:
                    # Restore the attempts count for error `Duplicate ticker ID`
                    # as it seems like sometimes IB cannot release the ID used
                    # as soon as it has responded the request while the
                    # reverse historical ticks request approaching the start
                    # time with all available ticks fetched and throws
                    # the duplicate ticker ID error.
                    attempts = attempts + 1 if attempts != -1 else attempts

                    next_end_time: datetime = err.err_extra

                    continue

                if attempts > 0:
                    if all_ticks:
                        # Updates the end time for next attempt
                        next_end_time = datetime.datetime.fromtimestamp(
                            all_ticks[0].time
                        ).astimezone(ib_client.IBClient.TZ)

                    continue

                if attempts == 0 and all_ticks:
                    print("Reached maximum attempts. Ending...")
                    break

                if attempts == 0 and not all_ticks:
                    raise err

        return {
            "ticks": all_ticks,
            "completed": False,
        }
    #endregion - Historical data

    #region - Live data
    async def stream_live_ticks(
        self, contract: ib_contract.Contract,
        listener: listeners.LiveTicksListener,
        tick_type: dt.LiveTicks=dt.LiveTicks.LAST
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
