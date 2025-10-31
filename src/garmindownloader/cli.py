"""
Command-line interface for the Garmin downloader.

Handles argument parsing and main entry point for the CLI.
"""

import argparse
import sys

from garmindownloader.downloader import fetch_data


def parse_months(month_str):
    """
    Parse the month parameter.

    :param month_str: The month parameter
    :return: List of months

    :exception argparse.ArgumentTypeError: If the month parameter is invalid
    """
    month_list = None

    if "-" in month_str:
        # Range of months
        try:
            start_month, end_month = map(int, month_str.split("-"))
        except ValueError as e:
            msg = "Invalid month range"
            raise argparse.ArgumentTypeError(msg) from e

        if start_month < 1 or end_month > 12 or start_month > end_month:
            msg = "Invalid month range"
            raise argparse.ArgumentTypeError(msg)

        month_list = list(range(start_month, end_month + 1))
    else:
        # Single month
        try:
            month = int(month_str)
        except ValueError as e:
            msg = "Month must be a number between 1 and 12"
            raise argparse.ArgumentTypeError(msg) from e

        if month < 1 or month > 12:
            raise argparse.ArgumentTypeError("Month must be a number between 1 and 12")

        month_list = [month]

    return month_list


def parse_command_line_args():
    """
    Parse and validate command line arguments.

    Parses command line arguments for year, month(s), and data type(s) to download.
    Validates that all datatypes are valid choices (bb or hr).

    :return: Parsed command line arguments with year, month list, and datatype list
    :raises SystemExit: If invalid arguments are provided (via argparse.ArgumentParser.error)
    """
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


def main():
    """
    Main entry point for the Garmin downloader script.

    Parses command line arguments and initiates the data download process.
    Errors are caught and printed to stderr.
    """
    args = parse_command_line_args()

    if args.year and args.month:
        try:
            fetch_data(args.year, args.month, args.datatype)
        except Exception as exc:
            print(exc, file=sys.stderr)


if __name__ == "__main__":
    main()
