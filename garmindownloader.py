"""
Downloads Body Battery and Heartrate data from Garmin Connect.

The data is downloaded in chunks of one month (the longest time period supported by Garmin Connect) and
saved in one CSV file per month.
"""

import argparse
import sys
import garminconnect
import os
import datetime
import csv
import calendar
from garth.exc import GarthHTTPError

GARMIN_TOKEN_DIR = "~/.garth"
GARMIN_TOKEN_ENV = "GARMINTOKENS"
DATATYPE_TO_FUNCTION = {
    "bb": {
        "func": "fetch_bb_data",
        "fieldnames": ["date", "charged", "drained", "max", "min"],
    },
    "hr": {"func": "fetch_hr_data", "fieldnames": ["timestamp", "heartrate"]},
}


class GarmindownloaderException(Exception):
    pass


def create_api_session():
    """Create a Garmin Connect API session."""
    token_store = os.getenv(GARMIN_TOKEN_ENV) or GARMIN_TOKEN_DIR

    try:
        garmin = garminconnect.Garmin()
        garmin.login(token_store)

        return garmin
    except (GarthHTTPError, AssertionError) as exc:
        raise (GarmindownloaderException(f"Error: {exc}")) from exc


def parse_months(month_str):
    """
    Parse the month parameter.

    :param month_str: The month parameter
    :return: List of months

    :exception argparse.ArgumentTypeError: If the month parameter is invalid
    """
    if "-" in month_str:
        # Range of months
        try:
            start_month, end_month = map(int, month_str.split("-"))
            if start_month < 1 or end_month > 12 or start_month > end_month:
                raise ValueError("Invalid month range")

            return list(range(start_month, end_month + 1))
        except ValueError as e:
            raise argparse.ArgumentTypeError(f"Invalid month range: {e}")
    else:
        # Single month
        try:
            month = int(month_str)
            if month < 1 or month > 12:
                raise ValueError("Month must be between 1 and 12")

            return [month]
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                "Month must be a number between 1 and 12"
            ) from exc


def parse_command_line_args():
    parser = argparse.ArgumentParser(description="Process year and month parameters.")
    parser.add_argument("year", type=int, help="The year (e.g., 2024).")
    parser.add_argument(
        "month",
        type=parse_months,
        help="Month or range of months (e.g., 5 or 5-8).",
    )
    parser.add_argument(
        "--datatype",
        required=True,
        type=lambda s: [item.strip() for item in s.split(",")],
        help="Data types to download: bb (Body Battery) and/or hr (Heart Rate). Example: --datatype bb,hr",
    )

    args = parser.parse_args()

    # Validate that all values are valid choices
    valid_choices = ["bb", "hr"]
    for dtype in args.datatype:
        if dtype not in valid_choices:
            parser.error(f"Invalid datatype '{dtype}'. Choose from {valid_choices}")

    return args


def fetch_bb_data(api, year, month):
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
    today = datetime.date.today()
    last_day_of_month = calendar.monthrange(year, month)[1]
    end_of_month = datetime.date(year, month, last_day_of_month)

    from_date = datetime.date(year, month, 1)
    to_date = end_of_month if end_of_month < today else today

    # Generate list of all days including end date
    date_list = [
        from_date + datetime.timedelta(days=i)
        for i in range((to_date - from_date).days + 1)
    ]
    return date_list


def write_data(data, filename, fieldnames):
    try:
        with open(filename, "w", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(
                csvfile, fieldnames=fieldnames, extrasaction="ignore"
            )
            writer.writeheader()
            writer.writerows(data)
    except (IOError, csv.Error) as exc:
        raise (GarmindownloaderException(f"Error writing CSV file: {exc}")) from exc


def fetch_data(year, months, datatype):
    api = create_api_session()

    for datatype in datatype:
        func = DATATYPE_TO_FUNCTION[datatype]["func"]
        fieldnames = DATATYPE_TO_FUNCTION[datatype]["fieldnames"]

        for month in months:
            data, filename = getattr(sys.modules[__name__], func)(api, year, month)

            write_data(data, filename, fieldnames)


def main():
    """Main function."""
    args = parse_command_line_args()

    if args.year and args.month:
        try:
            fetch_data(args.year, args.month, args.datatype)
        except Exception as exc:
            print(exc, file=sys.stderr)


if __name__ == "__main__":
    main()
