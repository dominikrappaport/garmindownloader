# Garmindownloader

## Author

Dominik Rappaport, dominik@rappaport.at

## Motivation

For comprehensive statistical analysis, it is advisable to download Garmin data to a local computer. This is particularly 
important because Garmin aggregates historical data after a certain period. The script retrieves both Body Battery and 
heart rate data from Garmin and stores them in CSV format. Since Garmin allows downloading a maximum of one month of 
data per request, the script automatically generates a separate CSV file for each month.

## Installation

The garmindownloader is distributed as a Python package. Several installation methods are available.

### Using pip

Executing `pip` installs the package in your current Python environment. Global installation was once possible, but
modern Linux distributions no longer permit this approach.

```bash
pip install garmindownloader
```

### Using pipx or uv

Both `pipx` and `uv` enable global tool installation. The package can be installed as follows:

```bash
pipx install garmindownloader
```

or

```bash
uv tools install garmindownloader
```

These steps assume you are using [uv](https://github.com/astral-sh/uv) as your package and project manager.

## Usage

### Authentication

First of all you need to create an authentication token for Garmin Connect. That can be done by running the
authenticate script.

```bash
garminauthenticate
```

You need to enter your Garmin Connect credentials and the script will generate a token and save it in the
`~/.garth` directory.

Once that is done the script can be run as follows. You specify a year and a month or a range of months and
if you want Body Battery data or heart rate data (or both).

```bash
garmindownloader <year> <month(s)> --datatype <datatype>
```

Examples:

```bash
garmindownloader --datatype hr 2025 9
garmindownloader --datatype bb,hr 2025 7-8
garmindownloader --datatype hr 2025 1
```

The script generates for each month a separate CSV file. For Body Battery, the files are names `bb<year><month>.csv`.
For heart rate data, the files are named `hr<year><month>.csv`.