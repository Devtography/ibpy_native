"""Model classes for order related data."""
import threading
from typing import List

from ibapi import contract as ib_contract
from ibapi import order as ib_order
from ibapi import order_state as ib_order_state

from ibpy_native.utils import datatype

class OpenOrder:
    """Provides info of an active open order.

    Args:
        contract (:obj:`ibapi.contract.Contract`): The order's contract.
        order (:obj:`ibapi.order.Order`): The current active order returned
            from IB.
        order_state (:obj:`ibapi.order_state.OrderState`): Order states/status
            returned from IB.
    """
    def __init__(self, contract: ib_contract.Contract, order: ib_order.Order,
                 order_state: ib_order_state.OrderState):
        self._lock = threading.Lock()
        # From `openOrder` callback
        self._contract = contract
        self._order = order
        self._order_state = order_state
        # From `orderStatus` callback
        self._status = datatype.OrderStatus(order_state.status)
        self._avg_fill_price = 0.0
        self._mkt_cap_price = 0.0
        self._exec_rec: List[datatype.OrderExecRec] = []

    @property
    def contract(self) -> ib_contract.Contract:
        """:obj:`ibapi.contract.Contract`: The order's contract. DO NOT modify
        the `Contract` returned!
        """
        return self._contract

    @property
    def order(self) -> ib_order.Order:
        """:obj:`ibapi.order.Order`: The order returned from IB. DO NOT modify
        the `Order` returned!

        Note:
            You should never monitor the value of the object returned from this
            property directly, as the underlying object will be replaced with
            the one returned from IB callback.
        """
        return self._order

    @property
    def order_state(self) -> ib_order_state.OrderState:
        """:obj:`ibapi.order_state.OrderState`: The order's states/status
        returned from IB. DO NOT modify the `OrderState` returned!

        Note:
            You should never monitor the value of the object returned from this
            property directly, as the underlying object will be replaced with
            the one returned from IB callback.
        """
        return self._order_state

    #region - From `Order` & `OrderState`
    @property
    def action(self) -> datatype.OrderAction:
        """:obj:`ibpy_native.utils.datatype.OrderAction`: Order's action.
        Either "BUY" or "SELL".
        """
        return datatype.OrderAction(self._order.action)

    @property
    def status(self) -> datatype.OrderStatus:
        """:obj:`ibpy_native.utils.datatype.OrderStatus`: The order's current
        status.
        """
        return self._status

    @property
    def filled(self) -> int:
        """int: The number of positions bought/sold."""
        return self._order.filledQuantity

    @property
    def quantity(self) -> int:
        """int: The number of positions being bought/sold."""
        return self._order.totalQuantity

    @property
    def commission(self) -> float:
        """float: The order's generated commission."""
        return self._order_state.commission
    #endregion - From `Order` & `OrderState`

    #region - From `orderStatus`
    @property
    def avg_fill_price(self) -> float:
        """float: Average filling price of the order.

        Note:
            Since IB does not guarante to return every change in order status,
            the value stored in this property might not be 100% accurate and
            should be used as reference only.
        """
        return self._avg_fill_price

    @property
    def mkt_cap_price(self) -> float:
        """float: Indicaes the current capped price if the order has been
        capped. Returns `0` if it isn't capped.

        Note:
            Since IB does not guarante to return every change in order status,
            the value stored in this property might not be 100% accurate and
            should be used as reference only.
        """
        return self._mkt_cap_price

    @property
    def exec_rec(self):
        """:obj:`tuple(ibpy_native.utils.datatype.OrderExecRec)`: The order
        execution record(s) returned from IB.

        Note:
            IB is not guaranteed to return every change in order status via the
            `orderStatus` callback. Therefore, DO NOT take this as an absolute
            reference for anything.
        """
        return tuple(self._exec_rec)
    #endregion - From `orderStatus`

    def order_update(self, order: ib_order.Order,
                    order_state: ib_order_state.OrderState):
        """INTERNAL FUNCTION! Thread-safe function to handle the order and
        order state updates from IB. DO NOT use this function in your own
        code unless you're testing something specifically.

        Args:
            order (:obj:`ibapi.order.Order`): The order returned from IB.
            order_state (:obj:`ibapi.order_state.OrderState`): The order
                current state returned from IB.
        """
        with self._lock:
            self._order = order
            self._order_state = order_state

    def order_status_update(self, status: datatype.OrderStatus, filled: float,
                            remaining: float, avg_fill_price: float,
                            last_fill_price: float, mkt_cap_price: float):
        """INTERNAL FUNCTION! Thread-safe function to handle the changes on
        order status updates from IB. DO NOT use this function in your own code
        unless you're testing something specifically.

        Args:
            status (:obj:`ibpy_native.utils.datatype.OrderStatus`): The order's
                current status.
            filled (float): Number of filled positions.
            remaining (float): The remnant positions.
            avg_fill_price (float): Average filling price.
            last_fill_price (float): Price at which the last positions were
                filled.
            mkt_cap_price (float): If an order has been capped, this indicates
                the current capped price.
        """
        with self._lock:
            self._status = status # Update order status no matter what

            if self._exec_rec:
                if self._exec_rec[-1].remaining == remaining:
                    # Filter out the duplicate messages returned from IB
                    return

            self._exec_rec.append(
                datatype.OrderExecRec(filled=filled, remaining=remaining,
                                        last_fill_price=last_fill_price)
            )
            self._avg_fill_price = avg_fill_price
            self._mkt_cap_price = mkt_cap_price
