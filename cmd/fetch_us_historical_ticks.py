"""
Script to fetch historical tick data from IB.
"""
import argparse
import time
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from ibpy_native import IBBridge
from ibpy_native.client import Const, IBClient
from ibpy_native.error import IBError
from ibapi.wrapper import Contract

class _FetchCmd:
    # pylint: disable=protected-access
    @classmethod
    def invoke(cls):
        """
        Invokes the command actions
        """
        cmd = cls.build_cmd()
        args = cmd.parse_args()
        args.func(args)

    @classmethod
    def build_cmd(cls) -> argparse.ArgumentParser:
        """
        Build the command line interface for historical ticks fetcher
        """

        # Create the top level parser
        parser = argparse.ArgumentParser(
            description="Fetch the historical ticks data for specified "
            "instrument from IB",
            formatter_class=argparse.RawTextHelpFormatter
        )
        # Arguments for Gateway/TWS config
        parser.add_argument(
            '-s', '--server-ip', dest='host', default='127.0.0.1', metavar='',
            help="specifies the IP of the running TWS/IB Gateway\n"
            "(default: 127.0.0.1)"
        )
        parser.add_argument(
            '-p', '--port', dest='port', default=4001, metavar='', type=int,
            help="specifies the socket port of TWS/IB Gateway\n"
            "(default: 4001)"
        )
        parser.add_argument(
            '-i', '--client-id', dest='client_id', default=1,
            metavar='', type=int,
            help="specifies the client ID for TWS/IB Gateway instance\n"
            "(default: 1)"
        )
        parser.add_argument(
            'symbol', help="specifies the symbol of the instrument"
        )
        sec_type_parsers = parser.add_subparsers(
            metavar='sec_type', required=True,
            help="specifies the security type to fetch"
        )

        # Create sub-commands
        cls._stk_cmd(sec_type_parsers)
        cls._fut_cmd(sec_type_parsers)

        return parser

    @classmethod
    def _add_common_args(cls, parser: argparse.ArgumentParser):
        parser.add_argument(
            '-dt', '--data-type', choices=['MIDPOINT', 'BIDASK', 'TRADES'],
            dest='data_type', default='TRADES', metavar='', type=str.upper,
            help="type of tick data requires\n"
            "options: {MIDPOINT, BIDASK, TRADES}\n"
            "(default: TRADES)"
        )
        parser.add_argument(
            '-f', '--from', dest='ft', metavar='',
            help="specifies the start date time of the ticks to be fetched\n"
            "format: {yyyyMMdd HH:mm:ss} (i.e. \"20200513 15:18:00\")\n"
            "* uses TWS/IB Gateway timezone specificed at login\n"
            "(default: from earliest available tick)"
        )
        parser.add_argument(
            '-t', '--to', dest='to', metavar='',
            help="specifies the end date time of the ticks to be fetched\n"
            "format: {yyyyMMdd HH:mm:ss} (i.e. \"20200513 15:18:00\")\n"
            "* uses TWS/IB Gateway timezone specificed at login\n"
            "(default: to latest available tick)"
        )
        parser.add_argument(
            '--timeout', dest='timeout', default=120,
            metavar='', type=int,
            help="specifies the second(s) to wait for the request\n"
            "(default: 120s)",
        )
        parser.add_argument(
            '-o', '--out', dest='out', metavar='',
            help="specifies the destination path & filename for the CSV file "
            "of tick data received\n"
            "(default: ./{data_type}/{symbol}-{sec_type}-{exchange}-{currency})"
            ".csv"
        )

    # Sub-command builders
    @classmethod
    def _stk_cmd(cls, parent: argparse._SubParsersAction):
        """
        Create the parser for the "stk" command
        """
        parser: argparse.ArgumentParser = parent.add_parser(
            'stk', aliases=['stock'], help=""
        )

        cls._add_common_args(parser)
        parser.set_defaults(func=cls._stk_actions)

    @classmethod
    def _fut_cmd(cls, parent: argparse._SubParsersAction):
        """
        Create the parser for the "fut" command
        """
        parser: argparse.ArgumentParser = parent.add_parser(
            'fut', aliases=['futures'], help=""
        )
        parser.formatter_class = argparse.RawTextHelpFormatter

        parser.add_argument(
            'contract_month', type=cls._validate_contract_month_format,
            help="specifies the contract month or date\n"
            "format: {yyyyMM(dd)} (i.e. 202003 or 20200320)"
        )
        cls._add_common_args(parser)
        parser.set_defaults(func=cls._fut_actions)

    @classmethod
    def _validate_contract_month_format(cls, value) -> int:
        int_value = int(value)

        if (len(value) != 6 and len(value) != 8) or not value.isdecimal():
            raise argparse.ArgumentTypeError(
                "%s is an invalid contract month" % value
            )

        return int_value

    # Sub-command functions
    @classmethod
    def _stk_actions(cls, args):
        bridge = cls._connect_ib_bridge(
            host=args.host, port=args.port, client_id=args.client_id
        )

        try:
            contract = bridge.get_us_stock_contract(symbol=args.symbol)
            cls._cmd_actions(bridge, contract, args)
        except IBError as err:
            cls._handles_ib_error(bridge, err)

    @classmethod
    def _fut_actions(cls, args):
        bridge = cls._connect_ib_bridge(
            host=args.host, port=args.port, client_id=args.client_id
        )

        try:
            contract = bridge.get_us_future_contract(
                symbol=args.symbol, contract_month=str(args.contract_month)
            )
            cls._cmd_actions(bridge, contract, args)
        except IBError as err:
            cls._handles_ib_error(bridge, err)

    # Sub-command common actions
    @classmethod
    def _connect_ib_bridge(cls, host: str, port: int,
                           client_id: int) -> IBBridge:
        print("Connecting to %s:%d..." % (host, port))
        bridge = IBBridge(host=host, port=port, client_id=client_id)

        # Wait for connection
        timeout = time.monotonic() + 10
        while time.monotonic() < timeout:
            if bridge.is_connected():
                print("Connected")

                return bridge

        print("Failed to connect to a running TWS/IB Gateway instance")
        sys.exit(1)

    @classmethod
    def _handles_ib_error(cls, bridge: IBBridge, err: IBError):
        print(err)

        if bridge.is_connected():
            bridge.disconnect()

        sys.exit(err.errorCode)

    @classmethod
    def _cmd_actions(cls, bridge: IBBridge, contract: Contract, args):
        print(contract)

        start_time: datetime = None
        end_time: datetime = datetime.now()

        if args.ft:
            start_time = datetime.strptime(args.ft, Const.TIME_FMT.value)
        if args.to:
            end_time = datetime.strptime(args.to, Const.TIME_FMT.value)

        if contract.lastTradeDateOrContractMonth != '':
            last_trade_time = datetime.strptime(
                contract.lastTradeDateOrContractMonth, '%Y%m%d'
            )
            last_trade_time = last_trade_time.replace(
                hour=23, minute=59, second=59
            ) + timedelta(seconds=1)

            if end_time > last_trade_time:
                end_time = last_trade_time

        if args.data_type == 'BIDASK':
            args.data_type = 'BID_ASK'

        fetch_result = bridge.get_historical_ticks(
            contract=contract, start=start_time, end=end_time,
            data_type=args.data_type, attempts=-1, timeout=args.timeout
        )

        if fetch_result['completed']:
            print("Data fetch completed")

        if bridge.is_connected():
            bridge.disconnect()

        # Export to csv
        ticks = []

        for tick in fetch_result['ticks']:
            content = vars(tick)
            content = {
                'readableTime':
                    datetime.fromtimestamp(tick.time).astimezone(IBClient.TZ),
                **content
            }
            ticks.append(content)

        data_frame = pd.DataFrame(ticks)

        if args.out is None:
            output_file = Path(
                f'./{args.data_type}/'
                f'{contract.symbol}-{contract.secType}-{contract.exchange}'
                f'-{contract.currency}.csv'
            )
        else:
            output_file = Path(args.out)

        output_file.parent.mkdir(parents=True, exist_ok=True)

        data_frame.to_csv(output_file)

        print(f"Data exported to {output_file.absolute()}")

        sys.exit()

if __name__ == '__main__':
    _FetchCmd.invoke()
