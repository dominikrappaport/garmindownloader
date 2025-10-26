"""
Authenticate a user with the Garth API.

The script will prompt the user for their email address and password,
and then save the authentication token to a file.
"""

from getpass import getpass

import garth

from garmindownloader.constants import GARMIN_TOKEN_DIR


def main():
    """
    Main entry point for the Garmin authentication script.

    Prompts the user for their email address and password,
    authenticates with Garmin Connect, and saves the token.
    """
    email = input("Enter email address: ")
    password = getpass("Enter password: ")
    garth.login(email, password)

    garth.save(GARMIN_TOKEN_DIR)
    print(f"Authentication successful! Token saved to {GARMIN_TOKEN_DIR}")


if __name__ == "__main__":
    main()
