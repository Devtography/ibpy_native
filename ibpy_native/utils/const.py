"""Constants use across the project."""
from typing_extensions import final, Final

@final
class _IB:
    # pylint: disable=too-few-public-methods
    """Constants use across the project."""

    # Defined constants
    TIME_FMT: Final[str] = '%Y%m%d %H:%M:%S' #IB time format

    # Messages
    MSG_TIMEOUT: Final[str] = (
        "Exceed maximum wait for wrapper to confirm finished"
    )
