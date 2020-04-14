from ib.wrapper import IBWrapper
from ib.client import IBClient

import threading

class IBStore(IBWrapper, IBClient):

    def __init__(self, host='127.0.0.1', port=4001, clientId=1, auto_conn=True):
        self.__host = host
        self.__port = port
        self.__clientId = clientId

        IBWrapper.__init__(self)
        IBClient.__init__(self, wrapper=self)

        if auto_conn:
            self.connect(host, port, clientId)
