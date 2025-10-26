"""
Constants used throughout the Garmin downloader library.
"""

GARMIN_TOKEN_DIR = "~/.garth"
GARMIN_TOKEN_ENV = "GARMINTOKENS"

DATATYPE_TO_FUNCTION = {
    "bb": {
        "func": "fetch_bb_data",
        "fieldnames": ["date", "charged", "drained", "max", "min"],
    },
    "hr": {"func": "fetch_hr_data", "fieldnames": ["timestamp", "heartrate"]},
}
