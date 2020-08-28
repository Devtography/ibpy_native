"""Code implementation of error related stuffs."""
import enum
from typing import Any

class IBErrorCode(enum.IntEnum):
    """Error codes."""
    # Error codes defined by IB
    DUPLICATE_TICKER_ID = 102
    INVALID_CONTRACT = 200
    # Self-defined error codes
    REQ_TIMEOUT = 50504
    RES_NO_CONTENT = 50204
    RES_UNEXPECTED = 50214
    QUEUE_IN_USE = 50400
    RES_NOT_FOUND = 50404
    UNKNOWN = 50500

class IBError(Exception):
    """Error object to handle the error retruns from IB."""

    def __init__(self, rid: int, err_code: int, err_str: str,
                 err_extra: Any = None):
        self.rid = rid
        self.err_code = err_code
        self.err_str = err_str
        self.err_extra = err_extra

        super().__init__(err_str)

    def __str__(self):
        # override method
        error_msg = "IB error id %d errorcode %d string %s" \
            % (self.rid, self.err_code, self.err_str)

        return error_msg
