"""
Code implementation of public interface to bridge between the package & IB API
"""
import random
import threading
from datetime import datetime, tzinfo
from typing import Optional, Union

from typing_extensions import Literal, TypedDict

from ibapi.wrapper import (Contract, HistoricalTick, HistoricalTickBidAsk,
                           HistoricalTickLast)
from .client import IBClient, Const
from .error import IBError, IBErrorCode
from .wrapper import IBWrapper

class IBTicksResult(TypedDict):
    """
    Use for type hint the returns of `IBBridge.get_historical_ticks`
    """
    ticks: Union[HistoricalTick, HistoricalTickBidAsk, HistoricalTickLast]
    completed: bool

class IBBridge:
    """
    Public class to bridge between `ibpy-native` & IB API
    """

    def __init__(self, host='127.0.0.1', port=4001,
                 client_id=1, auto_conn=True):
        self.__host = host
        self.__port = port
        self.__client_id = client_id

        self.__wrapper = IBWrapper()
        self.__client = IBClient(self.__wrapper)

        if auto_conn:
            self.connect()

    @staticmethod
    def set_timezone(tz: tzinfo):
        # pylint: disable=invalid-name
        """
        Set the timezone for the bridge to match the IB Gateway/TWS timezone
        specified at login.

        Default timezone `America/New_York` will be used if this function has
        never been called.

        * Value of `tz` should be returned from `pytz.timezone(zone: str)`
        """
        IBClient.TZ = tz


    def is_connected(self) -> bool:
        """
        Check if the bridge is connected to a running & logged in TWS/IB
        Gateway instance.
        """
        return self.__client.isConnected()

    def connect(self):
        """
        Connect the bridge to a running & logged in TWS/IB Gateway instance.
        """
        if not self.is_connected():
            self.__client.connect(self.__host, self.__port, self.__client_id)

            thread = threading.Thread(target=self.__client.run)
            thread.start()

            setattr(self.__client, "_thread", thread)

    def disconnect(self):
        """
        Disconnect the bridge from the connected TWS/IB Gateway instance.
        """
        self.__client.disconnect()

    def get_us_stock_contract(self, symbol: str,
                              timeout: int = IBClient.REQ_TIMEOUT) -> Contract:
        """
        Resolve the IB US stock contract
        """

        contract = Contract()
        contract.currency = 'USD'
        contract.exchange = 'SMART'
        contract.secType = 'STK'
        contract.symbol = symbol

        try:
            result = self.__client.resolve_contract(
                self.__gen_req_id(), contract, timeout
            )
        except IBError as err:
            raise err

        return result

    def get_us_future_contract(
            self, symbol: str, contract_month: Optional[str] = None,
            timeout: int = IBClient.REQ_TIMEOUT
        ) -> Contract:
        """
        Search the US future contract from IB.

        Ramarks:
          - The value of `contract_month` should be in format of `YYYYMM`. The
          current on going contract will be returned if it's left as `None`.
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

        contract = Contract()
        contract.currency = 'USD'
        contract.secType = 'FUT'
        contract.includeExpired = include_expired
        contract.symbol = symbol
        contract.lastTradeDateOrContractMonth = contract_month

        try:
            result = self.__client.resolve_contract(
                self.__gen_req_id(), contract, timeout
            )
        except IBError as err:
            raise err

        return result

    def get_earliest_data_point(
            self, contract: Contract,
            data_type: Literal['BID_ASK', 'TRADES'] = 'TRADES',
            timeout: int = IBClient.REQ_TIMEOUT
        ) -> datetime:
        """
        Returns the earliest data point of specified contract
        """
        if data_type not in {'BID_ASK', 'TRADES'}:
            raise ValueError(
                "Value of argument `data_type` can only be either 'BID_ASK' "
                "or 'TRADES'"
            )

        try:
            result = self.__client.resolve_head_timestamp(
                req_id=self.__gen_req_id(), contract=contract,
                show=data_type if data_type is 'TRADES' else 'BID',
                timeout=timeout
            )
        except (ValueError, IBError) as err:
            raise err

        data_point = datetime.fromtimestamp(result).astimezone(IBClient.TZ)

        return data_point.replace(tzinfo=None)

    def get_historical_ticks(
            self, contract: Contract,
            start: Optional[datetime] = None,
            end: datetime = datetime.now(),
            data_type: Literal['MIDPOINT', 'BID_ASK', 'TRADES'] = 'TRADES',
            attempts: int = 1, timeout: int = IBClient.REQ_TIMEOUT
        ) -> IBTicksResult:
        """
        Retrieve historical ticks data for specificed instrument/contract
        from IB
        """
        # Error checking
        if end.tzinfo is not None or (
                start is not None
                and start.tzinfo is not None
            ):
            raise ValueError(
                "Timezone should not be specified in either `start` or `end`."
            )

        if data_type not in {'MIDPOINT', 'BID_ASK', 'TRADES'}:
            raise ValueError(
                "Value of argument `data_type` can only be either 'MIDPOINT', "
                "'BID_ASK', or 'TRADES'"
            )

        try:
            head_timestamp = datetime.fromtimestamp(
                self.__client.resolve_head_timestamp(
                    self.__gen_req_id(), contract,
                    'TRADES' if data_type == 'TRADES' else 'BID',
                    timeout
                )
            ).astimezone(IBClient.TZ)
        except (ValueError, IBError) as err:
            raise err

        if end.timestamp() < head_timestamp.timestamp():
            raise ValueError(
                "Specificed end time is earlier than the earliest available "
                f"datapoint - {head_timestamp.strftime(Const.TIME_FMT.value)}"
            )

        if start is not None:
            if start.timestamp() < head_timestamp.timestamp():
                raise ValueError(
                    "Specificed start time is earlier than the earliest "
                    "available datapoint - "
                    + head_timestamp.strftime(Const.TIME_FMT.value)
                )
            if end.timestamp() < start.timestamp():
                raise ValueError(
                    "Specificed end time cannot be earlier than start time"
                )

            start = IBClient.TZ.localize(start)
        else:
            start = head_timestamp

        if attempts < 1 and attempts != -1:
            raise ValueError(
                "Value of argument `attempts` must be positive integer or -1"
            )

        # Process the request
        next_end_time = IBClient.TZ.localize(end)
        all_ticks = []

        while attempts > 0 or attempts == -1:
            attempts = attempts - 1 if attempts != -1 else attempts

            try:
                ticks = self.__client.fetch_historical_ticks(
                    self.__gen_req_id(), contract,
                    start, next_end_time, data_type, timeout
                )

                #  `ticks[1]` is a boolean represents if the data are all
                # fetched without timeout
                if ticks[1]:
                    ticks[0].extend(all_ticks)

                    return {
                        'ticks': ticks[0],
                        'completed': True
                    }

                ticks[0].extend(all_ticks)
                all_ticks = ticks[0]

                next_end_time = datetime.fromtimestamp(
                    ticks[0][0].time
                ).astimezone(IBClient.TZ)
            except ValueError as err:
                raise err
            except IBError as err:
                if err.err_code == IBErrorCode.DUPLICATE_TICKER_ID:
                    # Restore the attempts count for error `Duplicate ticker ID`
                    # as it shouldn't happen with the newly generated random
                    # number as ID, but sometimes IB just cannot release the
                    # ID used as soon as it has responded the request and throws
                    # the duplicate ticker ID error.
                    attempts = attempts + 1 if attempts != -1 else attempts

                    continue

                if attempts > 0:
                    if len(all_ticks) > 0:
                        # Updates the end time for next attempt
                        next_end_time = datetime.fromtimestamp(
                            all_ticks[0].time
                        ).astimezone(IBClient.TZ)

                    continue

                if attempts == 0 and len(all_ticks) > 0:
                    print("Reached maximum attempts. Ending...")
                    break

                if attempts == 0 and len(all_ticks) == 0:
                    raise err

        return {
            'ticks': all_ticks,
            'completed': False
        }

    def __gen_req_id(self) -> int:
        """
        Returns a random integer from 1 to 999999 as internal req_id for
        IB API requests
        """
        return random.randint(1, 999999)
