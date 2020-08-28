"""Listener interfaces for IB notification"""

import abc

class NotificationListener(metaclass=abc.ABCMeta):
    """Interface of listener for IB notification.

    Note:
        If IB returns error with `-1` for request identifier (`Id`), it
        indicates a notification and not true error condition.

    .. _TWS API v9.72+: EWrapper Interface Reference:
        https://interactivebrokers.github.io/tws-api/interfaceIBApi_1_1EWrapper.html#a0dd0ca408b9ef70181cec1e5ac938039
    """
    @abc.abstractmethod
    def on_notify(self, msg_code: int, msg: str):
        """Callback on notification receives.

        Args:
            msg_code (int): Code of system or warning message defined by IB.
            msg (:obj:`str`): TWS message.

        .. _TWS API v9.72+: Message Codes:
            https://interactivebrokers.github.io/tws-api/message_codes.html
        """
        return NotImplemented
        