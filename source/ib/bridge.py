from .wrapper import IBWrapper
from .client import IBClient

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

    def is_connected(self) -> bool:
        return self.__client.isConnected

    def connect(self):
        if not self.is_connected():
            self.__client.connect(self.__host, self.__port, self.__client_id)

            thread = threading.Thread(target=self.__client.run)
            thread.start()

            setattr(self.__client, "_thread", thread)

    def disconnect(self):
        self.__client.disconnect()
