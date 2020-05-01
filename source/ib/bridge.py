from .wrapper import IBWrapper
from .client import IBClient

from datetime import tzinfo

import threading

class IBBridge:

    def __init__(
        self, host='127.0.0.1', port=4001, client_id=1, auto_conn=True
    ):
        self.__host = host
        self.__port = port
        self.__client_id = client_id

        self.__wrapper = IBWrapper()
        self.__client = IBClient(self.__wrapper)

        if auto_conn:
            self.connect()

    @staticmethod
    def set_timezone(tz: tzinfo):
        """
        Set the timezone for the bridge to match the IB Gateway/TWS timezone 
        specified at login.

        Default timezone `America/New_York` will be used if this function has
        never been called.

        * Value of `tz` should be returned from `pytz.timezone(zone: str)`
        """
        IBClient.TZ = tz


    def is_connected(self) -> bool:
        return self.__client.isConnected()

    def connect(self):
        if not self.is_connected():
            self.__client.connect(self.__host, self.__port, self.__client_id)

            thread = threading.Thread(target=self.__client.run)
            thread.start()

            setattr(self.__client, "_thread", thread)

    def disconnect(self):
        self.__client.disconnect()
