"""
Code implementation for custom `FinishableQueue`
"""
import enum
import queue

# Queue status
class Status(enum.Enum):
    """
    Status codes for `FinishableQueue`
    """
    STARTED = 103
    ERROR = 500
    FINISHED = 200
    TIMEOUT = 408

class FinishableQueue():
    """
    This class takes a built-in `Queue` object to handle the async tasks by
    managing its' status based on elements retrieve from the `Queue` object.

    Args:
        queue_to_finish (:obj:`queue.Queue`): queue object assigned to handle
            the async task
    """
    def __init__(self, queue_to_finish: queue.Queue):
        self.__queue = queue_to_finish
        self.__status = Status.STARTED

    def get(self, timeout: int) -> list:
        """
        Returns a list of queue elements once timeout is finished, or a
        FINISHED flag is received in the queue.

        Args:
            timeout (int): Second(s) to wait before marking the task as timeout.

        Returns:
            list: The list of element(s) returned from the queue.
        """
        contents_of_queue = []

        while not self.__finished():
            try:
                current_element = self.__queue.get(timeout=timeout)

                if current_element is Status.FINISHED:
                    self.__status = Status.FINISHED
                elif current_element is Status.ERROR:
                    self.__status = Status.ERROR
                else:
                    contents_of_queue.append(current_element)
                    # then keep going and try and get more data

            except queue.Empty:
                self.__status = Status.TIMEOUT

        return contents_of_queue

    def get_status(self) -> Status:
        """
        Get status of the finishable queue.

        Returns:
            Status: Enum `Status` represents either the queue has been started,
                finished, timeout, or encountered error.
        """
        return self.__status

    def reset(self):
        """
        Reset the status to `STARTED` for reusing the queue if the
        status is marked as either `TIMEOUT` or `FINISHED`
        """
        if self.__finished():
            self.__status = Status.STARTED

    def __finished(self) -> bool:
        return (self.__status is Status.TIMEOUT
                or self.__status is Status.FINISHED
                or self.__status is Status.ERROR)
