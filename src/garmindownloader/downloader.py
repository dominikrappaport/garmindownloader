"""
Downloads Body Battery and Heartrate data from Garmin Connect.

The data is downloaded in chunks of one month (the longest time period supported by Garmin Connect) and
saved in one CSV file per month.
"""

import calendar
import csv
import datetime
import os
import sys

import garminconnect
from garth.exc import GarthHTTPError

from garmindownloader.constants import (
    DATATYPE_TO_FUNCTION,
    GARMIN_TOKEN_DIR,
    GARMIN_TOKEN_ENV,
)
from garmindownloader.exceptions import GarmindownloaderException


def create_api_session():
    """
    Create a Garmin Connect API session.

    Attempts to create and authenticate a Garmin Connect API session using
    stored authentication tokens. The token location is determined by the
    GARMINTOKENS environment variable, or defaults to ~/.garth if not set.

    :return: Authenticated Garmin Connect API object
    :raises GarmindownloaderException: If authentication fails or HTTP errors occur
    """
    token_store = os.getenv(GARMIN_TOKEN_ENV) or GARMIN_TOKEN_DIR

    try:
        garmin = garminconnect.Garmin()
        garmin.login(token_store)

        return garmin
    except (GarthHTTPError, AssertionError) as exc:
        raise (GarmindownloaderException(f"Error: {exc}")) from exc


def fetch_bb_data(api, year, month):
    """
    Fetch Body Battery data from Garmin Connect for a specific month.

    Downloads Body Battery data for all days in the specified month, calculating
    daily statistics including charged/drained values and min/max readings.

    :param api: Authenticated Garmin Connect API object
    :param year: The year to fetch data for
    :param month: The month to fetch data for (1-12)
    :return: Tuple containing list of Body Battery data dictionaries and output filename

    Each dictionary in the results list contains:
        - date: Date of the reading
        - charged: Amount of Body Battery charged
        - drained: Amount of Body Battery drained
        - max: Maximum Body Battery value for the day (or None if no data)
        - min: Minimum Body Battery value for the day (or None if no data)
    """
    filename = f"bb{year}{month:02d}.csv"
    results = []
    date_list = get_days_of_month(month, year)

    return_data = api.get_body_battery(
        date_list[0].isoformat(), date_list[-1].isoformat()
    )

    for day in return_data:
        readings = [v for _, v in day["bodyBatteryValuesArray"]]

        try:
            bbmax = max(readings)
        except (ValueError, TypeError):
            bbmax = None

        try:
            bbmin = min(readings)
        except (ValueError, TypeError):
            bbmin = None

        results.append({
            "date": day["date"],
            "charged": day["charged"],
            "drained": day["drained"],
            "max": bbmax,
            "min": bbmin,
        })

    return results, filename


def fetch_hr_data(api, year, month):
    """
    Fetch Heart Rate data from Garmin Connect for a specific month.

    Downloads all heart rate measurements for each day in the specified month,
    including timestamp and heart rate value for each reading.

    :param api: Authenticated Garmin Connect API object
    :param year: The year to fetch data for
    :param month: The month to fetch data for (1-12)
    :return: Tuple containing list of heart rate data dictionaries and output filename

    Each dictionary in the results list contains:
        - timestamp: DateTime of the heart rate reading
        - heartrate: Heart rate value in beats per minute
    """
    filename = f"hr{year}{month:02d}.csv"
    results = []
    date_list = get_days_of_month(month, year)

    for current_day in date_list:
        return_data = api.get_heart_rates(str(current_day))

        if return_data["heartRateValues"]:
            for timestamp, heart_rate in return_data["heartRateValues"]:
                results.append({
                    "timestamp": datetime.datetime.fromtimestamp(timestamp // 1000),
                    "heartrate": heart_rate,
                })

    return results, filename


def get_days_of_month(month, year):
    """
    Generate a list of all days in the specified month.

    Creates a list of datetime.date objects for each day in the given month,
    up to either the last day of the month or today's date (whichever is earlier).

    :param month: The month (1-12)
    :param year: The year
    :return: List of date objects representing each day in the month range
    """
    today = datetime.date.today()
    last_day_of_month = calendar.monthrange(year, month)[1]
    end_of_month = datetime.date(year, month, last_day_of_month)

    from_date = datetime.date(year, month, 1)
    to_date = min(today, end_of_month)

    # Generate list of all days including end date
    date_list = [
        from_date + datetime.timedelta(days=i)
        for i in range((to_date - from_date).days + 1)
    ]
    return date_list


def write_data(data, filename, fieldnames):
    """
    Write data to a CSV file.

    Creates a CSV file with the specified fieldnames and writes all data rows.
    Any extra fields in the data dictionaries that don't match fieldnames are ignored.

    :param data: List of dictionaries containing the data to write
    :param filename: Name of the output CSV file
    :param fieldnames: List of field names to use as CSV headers
    :raises GarmindownloaderException: If file writing fails due to I/O or CSV errors
    """
    try:
        with open(filename, "w", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(
                csvfile, fieldnames=fieldnames, extrasaction="ignore"
            )
            writer.writeheader()
            writer.writerows(data)
    except (OSError, csv.Error) as exc:
        raise (GarmindownloaderException(f"Error writing CSV file: {exc}")) from exc


def fetch_data(year, months, datatype):
    """
    Fetch and save Garmin data for specified months and data types.

    Creates an authenticated API session and downloads the requested data types
    (Body Battery and/or Heart Rate) for all specified months. Each month's data
    is saved to a separate CSV file.

    :param year: The year to fetch data for
    :param months: List of months to fetch data for (1-12)
    :param datatype: List of data types to fetch ('bb' for Body Battery, 'hr' for Heart Rate)
    :raises GarmindownloaderException: If API session creation or data writing fails
    """
    api = create_api_session()

    for datatype in datatype:
        func = DATATYPE_TO_FUNCTION[datatype]["func"]
        fieldnames = DATATYPE_TO_FUNCTION[datatype]["fieldnames"]

        for month in months:
            data, filename = getattr(sys.modules[__name__], func)(api, year, month)

            write_data(data, filename, fieldnames)
