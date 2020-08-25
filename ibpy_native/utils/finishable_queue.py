"""Code implementation for custom `_FinishableQueue`."""
import asyncio
import enum
import queue

from typing import Iterator, Any

# Queue status
class _Status(enum.Enum):
    """Status codes for `_FinishableQueue`"""
    STARTED = 103
    ERROR = 500
    FINISHED = 200
    TIMEOUT = 408

class _FinishableQueue():
    """This class takes a built-in `Queue` object to handle the async tasks by
    managing its' status based on elements retrieve from the `Queue` object.

    Args:
        queue_to_finish (:obj:`queue.Queue`): queue object assigned to handle
            the async task
    """
    def __init__(self, queue_to_finish: queue.Queue):
        self._queue = queue_to_finish
        self._status = _Status.STARTED

    @property
    def status(self) -> _Status:
        """Get status of the finishable queue.

        Returns:
            ibpy_native.utils.finishable_queue._Status: Enum `_Status`
                represents either the queue has been started, finished,
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
        return (self._status is _Status.TIMEOUT
                or self._status is _Status.FINISHED
                or self._status is _Status.ERROR)

    def reset(self):
        """Reset the status to `STARTED` for reusing the queue if the
        status is marked as either `TIMEOUT` or `FINISHED`
        """
        if self.finished:
            self._status = _Status.STARTED

    def put(self, element: Any):
        """Setter to put element to internal synchronised queue."""
        self._queue.put(element)

    async def get(self) -> list:
        """Returns a list of elements retrieved from queue once the FINISHED
        flag is received, or an exception is retrieved.

        Returns:
            list: The list of element(s) returned from the queue.
        """
        contents_of_queue = []
        loop = asyncio.get_event_loop()

        while not self.finished:
            current_element = await loop.run_in_executor(
                None, self._queue.get
            )

            if current_element is _Status.FINISHED:
                self._status = _Status.FINISHED
            else:
                if isinstance(current_element, BaseException):
                    self._status = _Status.ERROR

                contents_of_queue.append(current_element)

        return contents_of_queue

    async def stream(self) -> Iterator[Any]:
        """Yields the elements in queue as soon as an element has been put into
        the queue.
        """
        loop = asyncio.get_event_loop()

        while not self.finished:
            current_element = await loop.run_in_executor(
                None, self._queue.get
            )

            if current_element is _Status.FINISHED:
                self._status = current_element
            elif isinstance(current_element, BaseException):
                self._status = _Status.ERROR

            yield current_element
