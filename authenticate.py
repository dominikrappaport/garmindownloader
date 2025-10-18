"""
Authenticate a user with the Garth API.

The script will prompt the user for their email address and password,
and then save the authentication token to a file.
"""

from getpass import getpass

import garth

email = input("Enter email address: ")
password = getpass("Enter password: ")
garth.login(email, password)

garth.save("~/.garth")
