"""
Create new access tokens (for testing purposes) for the Google APIs.
"""
import os

from msl.io import (
    constants,
    GSheets,
    GDrive,
)

account = 'testing'
credentials = os.path.join(constants.HOME_DIR, account + '-client-secret.json')

GSheets(account=account, credentials=credentials, read_only=True)
GSheets(account=account, credentials=credentials, read_only=False)
GDrive(account=account, credentials=credentials, read_only=True)
GDrive(account=account, credentials=credentials, read_only=False)
