"""Sample script for fetching the historical tick data."""
import asyncio
import datetime
import os

import pandas as pd
import pytz

from ibapi import contract

import ibpy_native
from ibpy_native import error
from ibpy_native.interfaces import listeners
from ibpy_native.utils import datatype

class ConnectionListener(listeners.ConnectionListener):
    """Handles connection events."""
    def __init__(self):
        self.connected = False

    def on_connected(self):
        self.connected = True
        print("Connected")

    def on_disconnected(self):
        self.connected = False
        print("Disconnected")

class NotificationListener(listeners.NotificationListener):
    """Handles system notifications."""

    def on_notify(self, msg_code: int, msg: str):
        print(f"SYS_MSG (code: {msg_code}) - {msg}")

async def main():
    """Entry point"""
    gbp_usd_fx = contract.Contract()
    gbp_usd_fx.symbol = "GBP"
    gbp_usd_fx.secType = "CASH"
    gbp_usd_fx.currency = "USD"
    gbp_usd_fx.exchange = "IDEALPRO"

    connection_listener = ConnectionListener()

    bridge = ibpy_native.IBBridge(
        port=int(os.getenv("IB_PORT", "4002")),
        connection_listener=connection_listener,
        notification_listener=NotificationListener()
    )

    while not connection_listener.connected:
        await asyncio.sleep(1)

    contract_results = await bridge.search_detailed_contracts(
        contract=gbp_usd_fx)
    gbp_usd_fx = contract_results[0].contract
    print(f"Contract - {gbp_usd_fx}")

    tickers = []
    try:
        async for data in bridge.req_historical_ticks(
            contract=gbp_usd_fx,
            start=datetime.datetime(year=2021, month=1, day=4, hour=10),
            end=datetime.datetime(year=2021, month=1, day=4, hour=10, minute=5),
            tick_type=datatype.HistoricalTicks.BID_ASK,
            retry=5
        ):
            print(".", end="", flush=True)
            for tick in data.ticks:
                time = (datetime.datetime.fromtimestamp(tick.time)
                        .astimezone(pytz.timezone("America/New_York")))
                tickers.append({
                    "time": time,
                    "bid_price": tick.priceBid,
                    "ask_price": tick.priceAsk,
                    "bid_size": tick.sizeBid,
                    "ask_size": tick.sizeAsk,
                })
    except error.IBError as err:
        print(err)

        return

    cols = ["time", "bid_price", "ask_price", "bid_size", "ask_size"]
    dataframe = pd.DataFrame(data=tickers, columns=cols)
    print(dataframe)

    bridge.disconnect()

if __name__ == "__main__":
    print("Sample - fetch historical tick data")

    asyncio.run(main())
