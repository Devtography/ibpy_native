"""Global items use across the project."""
import datetime

import pytz
from typing_extensions import Final

# IB time format
TIME_FMT: Final[str] = "%Y%m%d %H:%M:%S"
# Timezone to match the one set in IB Gateway/TWS at login
TZ: datetime.tzinfo = pytz.timezone("America/New_York")
