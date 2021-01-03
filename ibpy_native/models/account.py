"""Models for IB account(s)."""
from typing_extensions import Final

class Account:
    """Model class for individual IB account.

    Attributes:
        account_id (:obj:`Final[str]`): Account ID received from IB Gateway.
    """
    account_id: Final[str]
    _destroy_flag: bool = False

    def __init__(self, account_id: str):
        self.account_id = account_id

    @property
    def destory_flag(self) -> bool:
        """Flag to indicate if this account instance is going to be destoried.

        Returns:
            bool: `True` if the corresponding account on IB is no longer
                available. No further action should be perfromed with this
                account instance if it's the case.
        """
        return self._destroy_flag

    def destory(self):
        """Marks the instance will be destoried and no further action should be
        performed on this instance.
        """
        self._destroy_flag = True