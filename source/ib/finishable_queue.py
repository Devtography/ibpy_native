import enum
import queue

# Queue status
class Status(enum.Enum):
    STARTED = 103
    FINISHED = 200
    TIMEOUT = 408

class FinishableQueue(object):
    def __init__(self, queue_to_finish: queue.Queue):
        self.__queue = queue_to_finish
        self.__status = Status.STARTED

    def get(self, timeout: int):
        """"
        Returns a list of queue elements once timeout is finished, or a FINISHED flag is received in the queue
        :param timeout: how long to wait before giving up
        :return: list of queue elements
        """
        contents_of_queue = []
        finished = False

        while not finished:
            try:
                current_element = self.__queue.get(timeout=timeout)

                if current_element is Status.FINISHED:
                    finished = True
                    self.__status = Status.FINISHED
                else:
                    contents_of_queue.append(current_element)
                    # then keep going and try and get more data

            except queue.Empty:
                finished = True
                self.__status = Status.TIMEOUT

        return contents_of_queue

    def get_status(self) -> Status:
        return self.__status
