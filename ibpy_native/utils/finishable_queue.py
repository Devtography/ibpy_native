"""Code implementation for custom `FinishableQueue`."""
import asyncio
import enum
import queue
import threading

from typing import AsyncIterator, Any

# Queue status
class Status(enum.Enum):
    """Status codes for `FinishableQueue`"""
    INIT = 0
    READY = 103
    ERROR = 500
    FINISHED = 200

class FinishableQueue():
    """Thread-safe class that takes a built-in `queue.Queue` object to handle
    the async tasks by managing its' status based on elements retrieve from the
    `Queue` object.

    Args:
        queue_to_finish (:obj:`queue.Queue`): queue object assigned to handle
            the async task
    """
    def __init__(self, queue_to_finish: queue.Queue):
        self._lock = threading.Lock()
        self._queue = queue_to_finish
        self._status = Status.INIT

    @property
    def status(self) -> Status:
        """:obj:`ibpy_native.utils.finishable_queue.Status`: Status represents
        wether the queue is newly initialised, ready for use, finished,
        timeout, or encountered error.
        """
        return self._status

    @property
    def finished(self) -> bool:
        """Indicates is the pervious task associated with this finishable queue
        finished.

        Returns:
            bool: True is task last associated is finished, False otherwise.
        """
        return self._status is Status.FINISHED

    def reset(self):
        """Reset the status to `READY` for reusing the queue if the
        status is marked as either `INIT` or `FINISHED`
        """
        if self.finished or self._status is Status.INIT:
            self._status = Status.READY

    def put(self, element: Any):
        """Setter to put element to internal synchronised queue."""
        if self._status is Status.INIT:
            with self._lock:
                self._status = Status.READY

        self._queue.put(element)

    async def get(self) -> list:
        """Returns a list of elements retrieved from queue once the FINISHED
        flag is received, or an exception is retrieved.

        Returns:
            list: The list of element(s) returned from the queue.
        """
        contents_of_queue = []
        loop = asyncio.get_event_loop()

        while not self.finished and self.status is not Status.ERROR:
            current_element = await loop.run_in_executor(
                None, self._queue.get
            )

            if current_element is Status.FINISHED:
                with self._lock:
                    self._status = Status.FINISHED
            else:
                if isinstance(current_element, BaseException):
                    with self._lock:
                        self._status = Status.ERROR

                contents_of_queue.append(current_element)

        return contents_of_queue

    async def stream(self) -> AsyncIterator[Any]:
        """Yields the elements in queue as soon as an element has been put into
        the queue.
        """
        loop = asyncio.get_event_loop()

        while not self.finished and self.status is not Status.ERROR:
            current_element = await loop.run_in_executor(
                None, self._queue.get
            )

            if current_element is Status.FINISHED:
                with self._lock:
                    self._status = current_element
            elif isinstance(current_element, BaseException):
                with self._lock:
                    self._status = Status.ERROR

            yield current_element
