from ibapi.wrapper import EWrapper
from ibapi.client import EClient

import threading

class Store(EWrapper, EClient):

    def __init__(self, host='127.0.0.1', port=4001, clientId=1, auto_conn=True):
        self.__host = host
        self.__port = port
        self.__clientId = clientId

        EWrapper.__init__(self)
        EClient.__init__(self, wrapper = self)

        if auto_conn:
            self.connect(host, port, clientId)
