"""Predefined contracts for unittest."""
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
    contract = ib_contract.Contract()
    contract.symbol = "YM"
    contract.secType = "FUT"
    contract.exchange = "ECBOT"
    contract.currency = "USD"
    contract.lastTradeDateOrContractMonth = "202009"

    return contract

def us_future_expired() -> ib_contract.Contract:
    """Expired US future - YM 2020.06"""
    contract = ib_contract.Contract()
    contract.symbol = "YM"
    contract.secType = "FUT"
    contract.exchange = "ECBOT"
    contract.currency = "USD"
    contract.lastTradeDateOrContractMonth = "202006"
    contract.includeExpired = True

    return contract
