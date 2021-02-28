"""Manager classes."""
# pylint: disable=protected-access
import asyncio
import datetime
import re
import threading
import queue
from typing import Dict, List, Optional, Union

from ibapi import common
from ibapi import contract as ib_contract
from ibapi import order as ib_order
from ibapi import order_state as ib_order_state

from ibpy_native import error
from ibpy_native import models
from ibpy_native._internal import _global
from ibpy_native.interfaces import delegates
from ibpy_native.interfaces import listeners
from ibpy_native.utils import datatype
from ibpy_native.utils import finishable_queue as fq

class AccountsManager(delegates.AccountsManagementDelegate):
    """Class to manage all IB accounts under the same username logged-in on
    IB Gateway.

    Args:
        accounts (:obj:`Dict[str, ibpy_native.models.Account]`, optional):
            Pre-populated accounts dictionary intended for test only. Defaults
            to `None`.
    """
    def __init__(self, accounts: Optional[Dict[str, models.Account]]=None):
        self._accounts: Dict[str, models.Account] = ({} if accounts is None
                                                     else accounts)
        self._account_updates_queue: fq.FinishableQueue = fq.FinishableQueue(
            queue_to_finish=queue.Queue()
        )

    @property
    def accounts(self) -> Dict[str, models.Account]:
        """:obj:`Dict[str, ibpy_native.models.Account]`: Dictionary of IB
        account(s) available under the same username logged in on the IB
        Gateway. Account IDs are used as keys.
        """
        # Implements `delegates._AccountListDelegate`
        return self._accounts

    @property
    def account_updates_queue(self) -> fq.FinishableQueue:
        """":obj:`ibpy_native.utils.finishable_queue.FinishableQueue`:
        The queue that stores account updates data from IB Gateway.
        """
        return self._account_updates_queue

    def on_account_list_update(self, account_list: List[str]):
        """Callback function for internal API callback
        `IBWrapper.managedAccounts`.

        Checks the existing account list for update(s) to the list. Terminates
        action(s) or subscription(s) on account(s) which is/are no longer
        available and removes from account list.

        Args:
            account_list (:obj:`List[str]`): List of proceeded account IDs
                updated from IB.
        """
        # Implements `delegates._AccountListDelegate`
        if self._accounts:
            # Deep clone the existing account dict for operation as modification
            # while iterating a iteratable will cause unexpected result.
            copied_dict: [str, models.Account] = self._accounts.copy()

            for acc_id in self._accounts:
                if acc_id not in account_list:
                    del copied_dict[acc_id]

            for acc_id in account_list:
                # if not any(ac.account_id == acc_id for ac in copied_dict):
                if acc_id not in copied_dict:
                    # Adds account appears in received list but not existing
                    # account dict so it can be managed by this framework.
                    copied_dict[acc_id] = models.Account(account_id=acc_id)

            # Clears the dict in instance scope then updates it instead of
            # reassigning its' pointer to the deep cloned list as the original
            # list may be referencing by the user via public property
            # `accounts`.
            self._accounts.clear()
            self._accounts.update(copied_dict)
        else:
            for acc_id in account_list:
                self._accounts[acc_id] = models.Account(account_id=acc_id)

    async def sub_account_updates(self, account: models.Account):
        """Subscribes to account updates.

        Args:
            account (:obj:`ibpy_native.models.Account`): The account to
                subscribe for updates.
        """
        await self._prevent_multi_account_updates()

        last_elm: Optional[Union[models.RawAccountValueData,
                                 models.RawPortfolioData,]] = None

        async for elm in self._account_updates_queue.stream():
            if isinstance(elm, (models.RawAccountValueData,
                                models.RawPortfolioData,)):
                if elm.account != account.account_id:
                    # Skip the current element incase the data received doesn't
                    # belong to the account specified, which shouldn't happen
                    # at all but just in case.
                    continue

                if isinstance(elm, models.RawAccountValueData):
                    self._update_account_value(account=account, data=elm)
                elif isinstance(elm, models.RawPortfolioData):
                    account.update_portfolio(contract_id=elm.contract.conId,
                                             data=elm)
            elif isinstance(elm, str):
                if last_elm is None:
                    # This case should not happen as the account update time
                    # is always received after the updated data.
                    continue

                if re.fullmatch(r"\d{2}:\d{2}", elm):
                    time = datetime.datetime.strptime(elm, "%H:%M").time()
                    time = time.replace(tzinfo=_global.TZ)

                    if isinstance(last_elm, (str, models.RawAccountValueData)):
                        # This timestamp represents the last update system time
                        # of the account values updated.
                        account.last_update_time = time
                    elif isinstance(last_elm, models.RawPortfolioData):
                        # This timestamp represents the last update system time
                        # of the portfolio data updated.
                        account.positions[
                            last_elm.contract.conId
                        ].last_update_time = time
            else:
                # In case if there's any unexpected element being passed
                # into this queue.
                continue

            last_elm = elm

    async def unsub_account_updates(self):
        """Unsubscribes to account updates."""
        self._account_updates_queue.put(fq.Status.FINISHED)

    def on_disconnected(self):
        if self._account_updates_queue.status is not (
            fq.Status.ERROR or fq.Status.FINISHED):
            err = error.IBError(
                rid=-1, err_code=error.IBErrorCode.NOT_CONNECTED,
                err_str=_global.MSG_NOT_CONNECTED
            )
            self._account_updates_queue.put(element=err)

    #region - Private functions
    async def _prevent_multi_account_updates(self):
        """Prevent multi subscriptions of account updates by verifying the
        `self._account_updates_queue` is finished or not as the API
        `ibapi.EClient.reqAccountUpdates` is designed as only one account at a
        time can be subscribed at a time.
        """
        if self._account_updates_queue.status is fq.Status.INIT:
            # Returns as no account updates request has been made before.
            return

        if not self._account_updates_queue.finished:
            self.unsub_account_updates()

            while not self._account_updates_queue.finished:
                await asyncio.sleep(0.1)

    def _update_account_value(self, account: models.Account,
                              data: models.RawAccountValueData):
        if data.key == "AccountReady":
            account.account_ready = (data.val == "true")
        else:
            account.update_account_value(key=data.key,
                                         currency=data.currency,
                                         val=data.val)
    #endregion - Private functions

class OrdersManager(delegates.OrdersManagementDelegate):
    """Class to handle orders related events."""
    def __init__(self,
                 event_listener: Optional[listeners.OrderEventsListener]=None):
        # Internal members
        self._lock = threading.Lock()
        self._listener = event_listener
        # Property
        self._next_order_id = 0
        self._open_orders: Dict[int, models.OpenOrder] = {}
        self._pending_queues: Dict[int, fq.FinishableQueue] = {}

    @property
    def next_order_id(self) -> int:
        return self._next_order_id

    @property
    def open_orders(self) -> Dict[int, models.OpenOrder]:
        return self._open_orders

    def is_pending_order(self, order_id: int) -> bool:
        if order_id in self._pending_queues:
            if self._pending_queues[order_id].status is fq.Status.INIT:
                return True

        return False

    #region - Internal functions
    def update_next_order_id(self, order_id: int):
        with self._lock:
            self._next_order_id = order_id

    def get_pending_queue(self, order_id: int) -> Optional[fq.FinishableQueue]:
        if order_id in self._pending_queues:
            return self._pending_queues[order_id]

        return None

    #region - Order events
    def order_error(self, err: error.IBError):
        if err.err_code == error.IBErrorCode.ORDER_MESSAGE:
            # Warning message only
            if self._listener:
                self._listener.on_warning(order_id=err.rid, msg=err.msg)
            return
        if err.rid in self._pending_queues:
            if self._listener is not None:
                self._listener.on_err(err)

            # Signals the order submission error
            if self._pending_queues[err.rid].status is not fq.Status.FINISHED:
                self._pending_queues[err.rid].put(element=err)

    def on_order_submission(self, order_id: int):
        """INTERNAL FUNCTION! Creates a new `FinishableQueue` with `order_id`
        as key in `_pending_queues` for order submission task completeion
        status monitoring.

        Args:
            order_id (int): The order's identifier on TWS/Gateway.

        Raises:
            ibpy_native.error.IBError: If existing `FinishableQueue` assigned
                for the `order_id` specificed is found.
        """
        if order_id not in self._pending_queues:
            self._pending_queues[order_id] = fq.FinishableQueue(
                queue_to_finish=queue.Queue()
            )
        else:
            raise error.IBError(
                rid=order_id, err_code=error.IBErrorCode.DUPLICATE_ORDER_ID,
                err_str=f"Existing queue assigned for order ID {order_id} "
                        "found. Possiblely duplicate order ID is being used."
            )

    def on_open_order_updated(
        self, contract: ib_contract.Contract, order: ib_order.Order,
        order_state: ib_order_state.OrderState
    ):
        if order.orderId in self._open_orders:
            self._open_orders[order.orderId].order_update(order, order_state)
            if (self._listener
                and order_state.status == datatype.OrderStatus.FILLED.value
                and order_state.commission != common.UNSET_DOUBLE):
                # Commission validation is to filter out the 1st incomplete
                # order filled status update.
                self._listener.on_filled(order=self._open_orders[order.orderId])
        else:
            self._open_orders[order.orderId] = models.OpenOrder(
                contract, order, order_state
            )
            if order.orderId in self._pending_queues:
                self._pending_queues[order.orderId].put(
                    element=fq.Status.FINISHED)

    def on_order_status_updated(
        self, order_id: int, status: str, filled: float, remaining: float,
        avg_fill_price: float, last_fill_price: float, mkt_cap_price: float
    ):
        if order_id in self._open_orders:
            self._open_orders[order_id].order_status_update(
                status=datatype.OrderStatus(status), filled=filled,
                remaining=remaining, avg_fill_price=avg_fill_price,
                last_fill_price=last_fill_price, mkt_cap_price=mkt_cap_price
            )

            if (self._listener
                and status == datatype.OrderStatus.CANCELLED.value):
                self._listener.on_cancelled(order=self._open_orders[order_id])

    def on_order_rejected(self, order_id: int, reason: str):
        if self._listener is not None and order_id in self._open_orders:
            self._listener.on_rejected(order=self._open_orders[order_id],
                                       reason=reason)
    #endregion - Order events

    def on_disconnected(self):
        for key, f_queue in self._pending_queues.items():
            if f_queue.status is not fq.Status.FINISHED or fq.Status.ERROR:
                err = error.IBError(
                    rid=key, err_code=error.IBErrorCode.NOT_CONNECTED,
                    err_str=_global.MSG_NOT_CONNECTED
                )
                f_queue.put(element=err)

        self._reset()
    #endregion - Internal functions

    def _reset(self):
        self._next_order_id = 0
        self._open_orders.clear()
        self._pending_queues.clear()
