"""Predefined contracts for unittest."""
import datetime

from ibapi import contract as ib_contract

def gbp_usd_fx() -> ib_contract.Contract:
    """FX GBP.USD"""
    contract = ib_contract.Contract()
    contract.symbol = "GBP"
    contract.secType = "CASH"
    contract.currency = "USD"
    contract.exchange = "IDEALPRO"

    return contract

def us_stock() -> ib_contract.Contract:
    """US stock - AAPL"""
    contract = ib_contract.Contract()
    contract.symbol = "AAPL"
    contract.secType = "STK"
    contract.exchange = "ISLAND"
    contract.currency = "USD"

    return contract

def us_future() -> ib_contract.Contract:
    """US future - YM"""
    # Generate contract month dynamically
    now = datetime.datetime.now()
    month = now.month
    for i in [3, 6, 9, 12]:
        if month < i:
            month = i
            break

    contract = ib_contract.Contract()
    contract.symbol = "YM"
    contract.secType = "FUT"
    contract.exchange = "ECBOT"
    contract.currency = "USD"
    contract.lastTradeDateOrContractMonth = f"{now.year}{month:02d}"

    return contract

def us_future_next() -> ib_contract.Contract:
    """US future - YM; Next contract month"""
    contract = us_future()
    year = int(contract.lastTradeDateOrContractMonth[:4])
    month = int(contract.lastTradeDateOrContractMonth[-2:])

    if month == 12:
        year += 1
        month = 3
    else:
        month += 3

    contract.lastTradeDateOrContractMonth = f"{year}{month:02d}"

    return contract

def us_future_expired() -> ib_contract.Contract:
    """Expired US future"""
    contract = ib_contract.Contract()
    contract.symbol = "YM"
    contract.secType = "FUT"
    contract.exchange = "ECBOT"
    contract.currency = "USD"
    # Targets the latest contract of last year
    contract.lastTradeDateOrContractMonth = (
        f"{datetime.datetime.now().year-1}12")
    contract.includeExpired = True

    return contract
