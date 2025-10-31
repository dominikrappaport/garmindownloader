"""
Garmin data downloader library.

Downloads Body Battery and Heart Rate data from Garmin Connect.
"""

from garmindownloader.cli import (
    main,
    parse_command_line_args,
    parse_months,
)
from garmindownloader.constants import (
    DATATYPE_TO_FUNCTION,
    GARMIN_TOKEN_DIR,
    GARMIN_TOKEN_ENV,
)
from garmindownloader.downloader import (
    create_api_session,
    fetch_bb_data,
    fetch_data,
    fetch_hr_data,
    get_days_of_month,
    write_data,
)
from garmindownloader.exceptions import GarmindownloaderError

__all__ = [
    "DATATYPE_TO_FUNCTION",
    # Constants
    "GARMIN_TOKEN_DIR",
    "GARMIN_TOKEN_ENV",
    # Exceptions
    "GarmindownloaderError",
    # Core downloader functions
    "create_api_session",
    "fetch_bb_data",
    "fetch_data",
    "fetch_hr_data",
    "get_days_of_month",
    "main",
    "parse_command_line_args",
    # CLI functions
    "parse_months",
    "write_data",
]


__version__ = "0.1.0"
__author__ = "Dominik Rappaport"
__email__ = "dominik@rappaport.at"
__license__ = "MIT"
__url__ = "https://github.com/rappaport/garmindownloader"
__description__ = "Garmin data downloader library."
__keywords__ = "garmin connect api download body battery heart rate"
__package_name__ = "garmindownloader"
__readme_name__ = "README.md"
