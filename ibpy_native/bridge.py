"""Code implementation of public interface to bridge between the package &
IB API.
"""
# pylint: disable=protected-access
import asyncio
import datetime
import threading
from typing import List, Optional

from deprecated import sphinx

from ibapi import contract as ib_contract

from ibpy_native import error
from ibpy_native.interfaces import listeners
from ibpy_native.internal import client as ib_client
from ibpy_native.internal import wrapper as ib_wrapper
from ibpy_native.utils import const
from ibpy_native.utils import datatype as dt

class IBBridge:
    """Public class to bridge between `ibpy-native` & IB API"""

    def __init__(self, host='127.0.0.1', port=4001, client_id=1, auto_conn=True,
                 notification_listener: \
                    Optional[listeners.NotificationListener] = None):
        self._host = host
        self._port = port
        self._client_id = client_id

        self._wrapper = ib_wrapper._IBWrapper(listener=notification_listener)
        self._client = ib_client._IBClient(wrapper=self._wrapper)

        if auto_conn:
            self.connect()

    # Setters
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
        ib_client._IBClient.TZ = tz

    def set_on_notify_listener(self, listener: listeners.NotificationListener):
        """Setter for optional `NotificationListener`.

        Args:
            listener (listeners.NotificationListener): Listener for IB
                notifications.
        """
        self._wrapper.set_on_notify_listener(listener=listener)

    # Connections
    def is_connected(self) -> bool:
        """Check if the bridge is connected to a running & logged in TWS/IB
        Gateway instance.
        """
        return self._client.isConnected()

    def connect(self):
        """Connect the bridge to a running & logged in TWS/IB Gateway instance.
        """
        if not self.is_connected():
            self._client.connect(self._host, self._port, self._client_id)

            thread = threading.Thread(target=self._client.run)
            thread.start()

            setattr(self._client, "_thread", thread)

    def disconnect(self):
        """Disconnect the bridge from the connected TWS/IB Gateway instance.
        """
        self._client.disconnect()

    ## Interacts with IB APIs
    # Contracts
    @sphinx.deprecated(
        version='0.2.0',
        reason="Function will be removed in the future if it's not compatible "
                "with the updates. Suggest to retrieve the contracts by using "
                "function `search_detailed_contract(contract)` instead."
    )
    async def get_us_stock_contract(self, symbol: str) -> ib_contract.Contract:
        """Resolve the IB US stock contract.

        Args:
            symbol (:obj:`str`): Symbol of the target instrument.

        Returns:
            ibapi.contract.Contract: Corresponding `Contract` object returned
                from IB.

        Raises:
            ibpy_native.error.IBError: If there is connection issue, or it
                failed to get additional contract details for the specified
                symbol.
        """

        contract = ib_contract.Contract()
        contract.currency = 'USD'
        contract.exchange = 'SMART'
        contract.secType = 'STK'
        contract.symbol = symbol

        try:
            result = await self._client.resolve_contract(
                req_id=self._wrapper.next_req_id, contract=contract
            )
        except error.IBError as err:
            raise err

        return result

    @sphinx.deprecated(
        version='0.2.0',
        reason="Function will be removed in the future if it's not compatible "
                "with the updates. Suggest to retrieve the contracts by using "
                "function `search_detailed_contract(contract)` instead."
    )
    async def get_us_future_contract(
            self, symbol: str, contract_month: Optional[str] = None
        ) -> ib_contract.Contract:
        """Search the US future contract from IB.

        Args:
            symbol (:obj:`str`): Symbol of the target instrument.
            contract_month (:obj:`str`, optional): Contract month for the
                target future contract in format - "YYYYMM". Defaults to None.

        Returns:
            ibapi.contract.Contract: Corresponding `Contract` object returned
                from IB. The current on going contract will be returned if
                `contract_month` is left as `None`.

        Raises:
            ibpy_native.error.IBError: If there is connection related issue,
                or it failed to get additional contract details for the
                specified symbol.
        """
        include_expired = False

        if contract_month is None:
            contract_month = ''
        else:
            if len(contract_month) != 6 or not contract_month.isdecimal():
                raise ValueError(
                    "Value of argument `contract_month` should be in format of "
                    "'YYYYMM'"
                )
            include_expired = True

        contract = ib_contract.Contract()
        contract.currency = 'USD'
        contract.secType = 'FUT'
        contract.includeExpired = include_expired
        contract.symbol = symbol
        contract.lastTradeDateOrContractMonth = contract_month

        try:
            result = await self._client.resolve_contract(
                req_id=self._wrapper.next_req_id, contract=contract
            )
        except error.IBError as err:
            raise err

        return result

    async def search_detailed_contracts(self, contract: ib_contract.Contract) \
        -> List[ib_contract.ContractDetails]:
        """Search the contracts with complete details from IB's database.

        Args:
            contract (:obj:`ibapi.contract.Contract): `Contract` object with
                partially completed info
                    - e.g. symbol, currency, etc...

        Returns:
            List[ibapi.contract.ContractDetails]: Fully fledged IB contract(s)
                with detailed info.

        Raises:
            ibpy_native.error.IBError: If
                - no result is found with the contract provided;
                - there's any error returned from IB.
        """
        try:
            res: List[ib_contract.ContractDetails] = await self._client\
                .resolve_contracts(req_id=self._wrapper.next_req_id,
                                   contract=contract)
        except error.IBError as err:
            raise err

        return  res

    # Historical data
    async def get_earliest_data_point(
            self, contract: ib_contract.Contract,
            data_type: Optional[dt.EarliestDataPoint] = \
                dt.EarliestDataPoint.TRADES
        ) -> datetime:
        """Returns the earliest data point of specified contract.

        Args:
            contract (:obj:`ibapi.contract.Contract`): `Contract` object with
                sufficient info to identify the instrument.
            data_type (Literal['BID_ASK', 'TRADES'], optional):
                Type of data for earliest data point. Defaults to 'TRADES'.

        Returns:
            datetime.datetime: The earliest data point for the specified
                contract in the timezone of whatever timezone set for this
                `IBBridge`.

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

        data_point = datetime.datetime.fromtimestamp(result)\
            .astimezone(ib_client._IBClient.TZ)

        return data_point.replace(tzinfo=None)

    async def get_historical_ticks(
            self, contract: ib_contract.Contract,
            start: datetime.datetime = None,
            end: Optional[datetime.datetime] = datetime.datetime.now(),
            data_type: Optional[dt.HistoricalTicks] = dt.HistoricalTicks.TRADES,
            attempts: Optional[int] = 1
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
            data_type (Literal['MIDPOINT', 'BID_ASK', 'TRADES'], optional):
                Type of data for the ticks. Defaults to 'TRADES'.
            attempts (int, optional): Attemp(s) to try requesting the historical
                ticks. Passing -1 into this argument will let the function
                retries for infinity times until all available ticks are received. Defaults to 1.

        Returns:
            IBTicksResult: Ticks returned from IB and a boolean to indicate if
                the returning object contains all available ticks.

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
        next_end_time = ib_client._IBClient.TZ.localize(dt=end)

        # Error checking
        if end.tzinfo is not None or (
                start is not None
                and start.tzinfo is not None
            ):
            raise ValueError(
                "Timezone should not be specified in either `start` or `end`."
            )

        try:
            head_timestamp = datetime.datetime.fromtimestamp(
                await self._client.resolve_head_timestamp(
                    req_id=self._wrapper.next_req_id, contract=contract,
                    show=dt.EarliestDataPoint.TRADES if \
                        data_type is dt.HistoricalTicks.TRADES \
                        else dt.EarliestDataPoint.BID
                )
            ).astimezone(tz=ib_client._IBClient.TZ)
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

            start = ib_client._IBClient.TZ.localize(dt=start)
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
                if res['completed']:
                    res['ticks'].extend(all_ticks)

                    return {
                        'ticks': res['ticks'],
                        'completed': True
                    }

                res['ticks'].extend(all_ticks)
                all_ticks = res['ticks']

                next_end_time = datetime.datetime.fromtimestamp(
                    res[0][0].time
                ).astimezone(ib_client._IBClient.TZ)
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
                        ).astimezone(ib_client._IBClient.TZ)

                    continue

                if attempts == 0 and all_ticks:
                    print("Reached maximum attempts. Ending...")
                    break

                if attempts == 0 and not all_ticks:
                    raise err

        return {
            'ticks': all_ticks,
            'completed': False
        }

    # Live data
    async def stream_live_ticks(
            self, contract: ib_contract.Contract,
            listener: listeners.LiveTicksListener,
            tick_type: Optional[dt.LiveTicks] = dt.LiveTicks.LAST
        ) -> int:
        """Request to stream live tick data.

        Args:
            contract (:obj:`ibapi.contract.Contract`): `Contract` object with
                sufficient info to identify the instrument.
            listener (:obj:`ibpy_native.interfaces.listenersLiveTicksListener`):
                Callback listener for receiving ticks, finish signale, and
                error from IB API.
            tick_type (:obj:`TickType`, optional): Type of ticks to be
                requested. Defaults to `TickType.LAST`.

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
