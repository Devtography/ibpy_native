from ibapi.wrapper import EWrapper

import queue

class IBWrapper(EWrapper):
    """
    The wrapper deals with the action coming back from the IB gateway or 
    TWS instance
    """

    def __init__(self):
        self.__err_queue = queue.Queue()

        super().__init__(self)

    ## Error handling
    def has_err(self):
        return not self.__err_queue.empty()
 
    def get_err(self, timeout=10):
        if self.has_err():
            try:
                return self.__err_queue.get(timeout=timeout)
            except queue.Empty:
                return None

        return None
       
    def error(self, id, errorCode, errorString):
        ## Overridden method
        error_msg = "IB error id %d errorcode %d string %s" \
            % (id, errorCode, errorString)

        self.__err_queue.put(error_msg)
