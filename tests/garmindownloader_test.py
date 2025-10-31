"""
Unit tests for the garmindownloader module.
"""

import argparse
import csv
import datetime
import os
from io import StringIO
from unittest.mock import Mock, mock_open, patch

import pytest

from garmindownloader.cli import (
    main,
    parse_command_line_args,
    parse_months,
)
from garmindownloader.downloader import (
    GARMIN_TOKEN_DIR,
    GARMIN_TOKEN_ENV,
    GarmindownloaderError,
    create_api_session,
    fetch_bb_data,
    fetch_data,
    fetch_hr_data,
    get_days_of_month,
    write_data,
)


class TestCreateApiSession:
    """Tests for create_api_session function."""

    @patch.dict(os.environ, {}, clear=True)
    @patch("garmindownloader.downloader.garminconnect.Garmin")
    def test_create_api_session_default_token_dir(self, mock_garmin_class):
        """Test API session creation with default token directory."""
        mock_garmin_instance = Mock()
        mock_garmin_class.return_value = mock_garmin_instance

        result = create_api_session()

        mock_garmin_class.assert_called_once()
        mock_garmin_instance.login.assert_called_once_with(GARMIN_TOKEN_DIR)
        assert result == mock_garmin_instance

    @patch.dict(os.environ, {GARMIN_TOKEN_ENV: "/custom/path"})
    @patch("garmindownloader.downloader.garminconnect.Garmin")
    def test_create_api_session_custom_token_dir(self, mock_garmin_class):
        """Test API session creation with custom token directory from environment."""
        mock_garmin_instance = Mock()
        mock_garmin_class.return_value = mock_garmin_instance

        result = create_api_session()

        mock_garmin_instance.login.assert_called_once_with("/custom/path")
        assert result == mock_garmin_instance

    @patch("garmindownloader.downloader.garminconnect.Garmin")
    def test_create_api_session_assertion_error(self, mock_garmin_class):
        """Test API session creation handles AssertionError."""
        mock_garmin_instance = Mock()
        mock_garmin_class.return_value = mock_garmin_instance
        mock_garmin_instance.login.side_effect = AssertionError("Auth failed")

        with pytest.raises(GarmindownloaderError, match="Error: Auth failed"):
            create_api_session()


class TestParseMonths:
    """Tests for parse_months function."""

    def test_parse_single_month(self):
        """Test parsing a single month."""
        assert parse_months("5") == [5]
        assert parse_months("1") == [1]
        assert parse_months("12") == [12]

    def test_parse_month_range(self):
        """Test parsing a range of months."""
        assert parse_months("5-8") == [5, 6, 7, 8]
        assert parse_months("1-3") == [1, 2, 3]
        assert parse_months("10-12") == [10, 11, 12]

    def test_parse_single_month_range(self):
        """Test parsing a range with same start and end month."""
        assert parse_months("7-7") == [7]

    def test_parse_invalid_single_month_too_low(self):
        """Test parsing an invalid single month (too low)."""
        with pytest.raises(
            argparse.ArgumentTypeError, match="Month must be a number between 1 and 12"
        ):
            parse_months("0")

    def test_parse_invalid_single_month_too_high(self):
        """Test parsing an invalid single month (too high)."""
        with pytest.raises(
            argparse.ArgumentTypeError, match="Month must be a number between 1 and 12"
        ):
            parse_months("13")

    def test_parse_invalid_month_range_start_too_low(self):
        """Test parsing an invalid month range (start < 1)."""
        with pytest.raises(argparse.ArgumentTypeError, match="Invalid month range"):
            parse_months("0-5")

    def test_parse_invalid_month_range_end_too_high(self):
        """Test parsing an invalid month range (end > 12)."""
        with pytest.raises(argparse.ArgumentTypeError, match="Invalid month range"):
            parse_months("10-13")

    def test_parse_invalid_month_range_start_greater_than_end(self):
        """Test parsing an invalid month range (start > end)."""
        with pytest.raises(argparse.ArgumentTypeError, match="Invalid month range"):
            parse_months("8-5")

    def test_parse_invalid_string(self):
        """Test parsing an invalid string."""
        with pytest.raises(
            argparse.ArgumentTypeError, match="Month must be a number between 1 and 12"
        ):
            parse_months("abc")

    def test_parse_invalid_range_string(self):
        """Test parsing an invalid range string."""
        with pytest.raises(argparse.ArgumentTypeError, match="Invalid month range"):
            parse_months("a-b")


class TestParseCommandLineArgs:
    """Tests for parse_command_line_args function."""

    @patch("sys.argv", ["script.py", "2024", "5", "--datatype", "bb"])
    def test_parse_args_single_month_single_datatype(self):
        """Test parsing single month and single datatype."""
        args = parse_command_line_args()
        assert args.year == 2024
        assert args.month == [5]
        assert args.datatype == ["bb"]

    @patch("sys.argv", ["script.py", "2023", "5-8", "--datatype", "bb,hr"])
    def test_parse_args_range_and_multiple_datatypes(self):
        """Test parsing month range and multiple datatypes."""
        args = parse_command_line_args()
        assert args.year == 2023
        assert args.month == [5, 6, 7, 8]
        assert args.datatype == ["bb", "hr"]

    @patch("sys.argv", ["script.py", "2024", "5", "--datatype", "invalid"])
    def test_parse_args_invalid_datatype(self):
        """Test parsing with invalid datatype."""
        with pytest.raises(SystemExit):
            parse_command_line_args()

    @patch("sys.argv", ["script.py", "2024", "5", "--datatype", "bb,invalid,hr"])
    def test_parse_args_one_invalid_datatype_in_list(self):
        """Test parsing with one invalid datatype in list."""
        with pytest.raises(SystemExit):
            parse_command_line_args()

    @patch("sys.argv", ["script.py", "2024", "5"])
    def test_parse_args_missing_datatype(self):
        """Test parsing without required datatype argument."""
        with pytest.raises(SystemExit):
            parse_command_line_args()


class TestFetchBbData:
    """Tests for fetch_bb_data function."""

    def test_fetch_bb_data_normal_case(self):
        """Test fetching Body Battery data with normal values."""
        mock_api = Mock()
        mock_api.get_body_battery.return_value = [
            {
                "date": "2024-05-01",
                "charged": 50,
                "drained": 40,
                "bodyBatteryValuesArray": [(1, 30), (2, 50), (3, 70)],
            },
            {
                "date": "2024-05-02",
                "charged": 60,
                "drained": 45,
                "bodyBatteryValuesArray": [(1, 25), (2, 55), (3, 65)],
            },
        ]

        results, filename = fetch_bb_data(mock_api, 2024, 5)

        assert filename == "bb202405.csv"
        assert len(results) == 2
        assert results[0] == {
            "date": "2024-05-01",
            "charged": 50,
            "drained": 40,
            "max": 70,
            "min": 30,
        }
        assert results[1] == {
            "date": "2024-05-02",
            "charged": 60,
            "drained": 45,
            "max": 65,
            "min": 25,
        }

    def test_fetch_bb_data_empty_values(self):
        """Test fetching Body Battery data with empty values array."""
        mock_api = Mock()
        mock_api.get_body_battery.return_value = [
            {
                "date": "2024-05-01",
                "charged": 0,
                "drained": 0,
                "bodyBatteryValuesArray": [],
            }
        ]

        results, filename = fetch_bb_data(mock_api, 2024, 5)

        assert filename == "bb202405.csv"
        assert len(results) == 1
        assert results[0]["max"] is None
        assert results[0]["min"] is None

    def test_fetch_bb_data_single_digit_month(self):
        """Test filename format for single digit month."""
        mock_api = Mock()
        mock_api.get_body_battery.return_value = []

        results, filename = fetch_bb_data(mock_api, 2024, 3)

        assert filename == "bb202403.csv"

    def test_fetch_bb_data_double_digit_month(self):
        """Test filename format for double digit month."""
        mock_api = Mock()
        mock_api.get_body_battery.return_value = []

        results, filename = fetch_bb_data(mock_api, 2024, 11)

        assert filename == "bb202411.csv"


class TestFetchHrData:
    """Tests for fetch_hr_data function."""

    @patch("garmindownloader.downloader.get_days_of_month")
    def test_fetch_hr_data_normal_case(self, mock_get_days):
        """Test fetching heart rate data with normal values."""
        mock_get_days.return_value = [
            datetime.date(2024, 5, 1),
            datetime.date(2024, 5, 2),
        ]

        mock_api = Mock()
        mock_api.get_heart_rates.side_effect = [
            {"heartRateValues": [(1714550400000, 60), (1714554000000, 65)]},
            {"heartRateValues": [(1714636800000, 70)]},
        ]

        results, filename = fetch_hr_data(mock_api, 2024, 5)

        assert filename == "hr202405.csv"
        assert len(results) == 3
        assert results[0]["heartrate"] == 60
        assert results[1]["heartrate"] == 65
        assert results[2]["heartrate"] == 70

    @patch("garmindownloader.downloader.get_days_of_month")
    def test_fetch_hr_data_empty_values(self, mock_get_days):
        """Test fetching heart rate data with no values."""
        mock_get_days.return_value = [datetime.date(2024, 5, 1)]

        mock_api = Mock()
        mock_api.get_heart_rates.return_value = {"heartRateValues": None}

        results, filename = fetch_hr_data(mock_api, 2024, 5)

        assert filename == "hr202405.csv"
        assert len(results) == 0

    @patch("garmindownloader.downloader.get_days_of_month")
    def test_fetch_hr_data_empty_list(self, mock_get_days):
        """Test fetching heart rate data with empty list."""
        mock_get_days.return_value = [datetime.date(2024, 5, 1)]

        mock_api = Mock()
        mock_api.get_heart_rates.return_value = {"heartRateValues": []}

        results, filename = fetch_hr_data(mock_api, 2024, 5)

        assert filename == "hr202405.csv"
        assert len(results) == 0


class TestGetDaysOfMonth:
    """Tests for get_days_of_month function."""

    @patch("garmindownloader.downloader.datetime")
    def test_get_days_of_month_complete_month_in_past(self, mock_datetime):
        """Test getting days for a complete month in the past."""
        mock_datetime.date.today.return_value = datetime.date(2024, 6, 15)
        mock_datetime.date.side_effect = lambda *args, **kw: datetime.date(*args, **kw)
        mock_datetime.timedelta = datetime.timedelta

        result = get_days_of_month(5, 2024)

        assert len(result) == 31
        assert result[0] == datetime.date(2024, 5, 1)
        assert result[-1] == datetime.date(2024, 5, 31)

    @patch("garmindownloader.downloader.datetime")
    def test_get_days_of_month_current_month_partial(self, mock_datetime):
        """Test getting days for current month up to today."""
        mock_datetime.date.today.return_value = datetime.date(2024, 5, 15)
        mock_datetime.date.side_effect = lambda *args, **kw: datetime.date(*args, **kw)
        mock_datetime.timedelta = datetime.timedelta

        result = get_days_of_month(5, 2024)

        assert len(result) == 15
        assert result[0] == datetime.date(2024, 5, 1)
        assert result[-1] == datetime.date(2024, 5, 15)

    @patch("garmindownloader.downloader.datetime")
    def test_get_days_of_month_february_leap_year(self, mock_datetime):
        """Test getting days for February in a leap year."""
        mock_datetime.date.today.return_value = datetime.date(2024, 6, 1)
        mock_datetime.date.side_effect = lambda *args, **kw: datetime.date(*args, **kw)
        mock_datetime.timedelta = datetime.timedelta

        result = get_days_of_month(2, 2024)

        assert len(result) == 29
        assert result[-1] == datetime.date(2024, 2, 29)

    @patch("garmindownloader.downloader.datetime")
    def test_get_days_of_month_february_non_leap_year(self, mock_datetime):
        """Test getting days for February in a non-leap year."""
        mock_datetime.date.today.return_value = datetime.date(2023, 6, 1)
        mock_datetime.date.side_effect = lambda *args, **kw: datetime.date(*args, **kw)
        mock_datetime.timedelta = datetime.timedelta

        result = get_days_of_month(2, 2023)

        assert len(result) == 28
        assert result[-1] == datetime.date(2023, 2, 28)

    @patch("garmindownloader.downloader.datetime")
    def test_get_days_of_month_single_day(self, mock_datetime):
        """Test getting days when today is the first day of month."""
        mock_datetime.date.today.return_value = datetime.date(2024, 5, 1)
        mock_datetime.date.side_effect = lambda *args, **kw: datetime.date(*args, **kw)
        mock_datetime.timedelta = datetime.timedelta

        result = get_days_of_month(5, 2024)

        assert len(result) == 1
        assert result[0] == datetime.date(2024, 5, 1)


class TestWriteData:
    """Tests for write_data function."""

    def test_write_data_normal_case(self):
        """Test writing data to CSV file."""
        data = [
            {"field1": "value1", "field2": "value2"},
            {"field1": "value3", "field2": "value4"},
        ]
        fieldnames = ["field1", "field2"]

        m = mock_open()
        with patch("builtins.open", m):
            write_data(data, "test.csv", fieldnames)

        m.assert_called_once_with("test.csv", "w", encoding="utf-8")
        handle = m()
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)

        assert "field1,field2" in written_content
        assert "value1,value2" in written_content
        assert "value3,value4" in written_content

    def test_write_data_with_extra_fields(self):
        """Test writing data with extra fields that should be ignored."""
        data = [
            {"field1": "value1", "field2": "value2", "extra": "ignored"},
        ]
        fieldnames = ["field1", "field2"]

        m = mock_open()
        with patch("builtins.open", m):
            write_data(data, "test.csv", fieldnames)

        handle = m()
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)

        assert "extra" not in written_content
        assert "field1,field2" in written_content

    def test_write_data_io_error(self):
        """Test handling of IO error during write."""
        data = [{"field1": "value1"}]
        fieldnames = ["field1"]

        with patch("builtins.open", side_effect=OSError("Disk full")):
            with pytest.raises(GarmindownloaderError, match="Error writing CSV file"):
                write_data(data, "test.csv", fieldnames)

    def test_write_data_csv_error(self):
        """Test handling of CSV error during write."""
        data = [{"field1": "value1"}]
        fieldnames = ["field1"]

        m = mock_open()
        with patch("builtins.open", m):
            with patch("csv.DictWriter") as mock_writer_class:
                mock_writer = Mock()
                mock_writer_class.return_value = mock_writer
                mock_writer.writerows.side_effect = csv.Error("CSV error")

                with pytest.raises(
                    GarmindownloaderError, match="Error writing CSV file"
                ):
                    write_data(data, "test.csv", fieldnames)


class TestFetchData:
    """Tests for fetch_data function."""

    @patch("garmindownloader.downloader.create_api_session")
    @patch("garmindownloader.downloader.fetch_bb_data")
    @patch("garmindownloader.downloader.write_data")
    def test_fetch_data_single_month_single_type(
        self, mock_write, mock_fetch_bb, mock_create_api
    ):
        """Test fetching data for single month and single datatype."""
        mock_api = Mock()
        mock_create_api.return_value = mock_api
        mock_fetch_bb.return_value = ([{"date": "2024-05-01"}], "bb202405.csv")

        fetch_data(2024, [5], ["bb"])

        mock_create_api.assert_called_once()
        mock_fetch_bb.assert_called_once_with(mock_api, 2024, 5)
        mock_write.assert_called_once_with(
            [{"date": "2024-05-01"}],
            "bb202405.csv",
            ["date", "charged", "drained", "max", "min"],
        )

    @patch("garmindownloader.downloader.create_api_session")
    @patch("garmindownloader.downloader.fetch_hr_data")
    @patch("garmindownloader.downloader.write_data")
    def test_fetch_data_multiple_months(
        self, mock_write, mock_fetch_hr, mock_create_api
    ):
        """Test fetching data for multiple months."""
        mock_api = Mock()
        mock_create_api.return_value = mock_api
        mock_fetch_hr.side_effect = [
            ([{"timestamp": "2024-05-01"}], "hr202405.csv"),
            ([{"timestamp": "2024-06-01"}], "hr202406.csv"),
        ]

        fetch_data(2024, [5, 6], ["hr"])

        assert mock_fetch_hr.call_count == 2
        assert mock_write.call_count == 2

    @patch("garmindownloader.downloader.create_api_session")
    @patch("garmindownloader.downloader.fetch_bb_data")
    @patch("garmindownloader.downloader.fetch_hr_data")
    @patch("garmindownloader.downloader.write_data")
    def test_fetch_data_multiple_datatypes(
        self, mock_write, mock_fetch_hr, mock_fetch_bb, mock_create_api
    ):
        """Test fetching multiple datatypes."""
        mock_api = Mock()
        mock_create_api.return_value = mock_api
        mock_fetch_bb.return_value = ([{"date": "2024-05-01"}], "bb202405.csv")
        mock_fetch_hr.return_value = ([{"timestamp": "2024-05-01"}], "hr202405.csv")

        fetch_data(2024, [5], ["bb", "hr"])

        mock_fetch_bb.assert_called_once()
        mock_fetch_hr.assert_called_once()
        assert mock_write.call_count == 2


class TestMain:
    """Tests for main function."""

    @patch("garmindownloader.cli.parse_command_line_args")
    @patch("garmindownloader.cli.fetch_data")
    def test_main_success(self, mock_fetch_data, mock_parse_args):
        """Test main function with successful execution."""
        mock_args = Mock()
        mock_args.year = 2024
        mock_args.month = [5]
        mock_args.datatype = ["bb"]
        mock_parse_args.return_value = mock_args

        main()

        mock_parse_args.assert_called_once()
        mock_fetch_data.assert_called_once_with(2024, [5], ["bb"])

    @patch("garmindownloader.cli.parse_command_line_args")
    @patch("garmindownloader.cli.fetch_data")
    @patch("sys.stderr", new_callable=StringIO)
    def test_main_exception_handling(
        self, mock_stderr, mock_fetch_data, mock_parse_args
    ):
        """Test main function handles exceptions."""
        mock_args = Mock()
        mock_args.year = 2024
        mock_args.month = [5]
        mock_args.datatype = ["bb"]
        mock_parse_args.return_value = mock_args
        mock_fetch_data.side_effect = Exception("Test error")

        main()

        assert "Test error" in mock_stderr.getvalue()

    @patch("garmindownloader.cli.parse_command_line_args")
    @patch("garmindownloader.cli.fetch_data")
    def test_main_no_year_or_month(self, mock_fetch_data, mock_parse_args):
        """Test main function when year or month is missing."""
        mock_args = Mock()
        mock_args.year = None
        mock_args.month = None
        mock_parse_args.return_value = mock_args

        main()

        mock_fetch_data.assert_not_called()
