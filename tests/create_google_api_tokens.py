"""
Create new access tokens for the Google APIs.
"""
import os

from msl.io import GDrive
from msl.io import GMail
from msl.io import GSheets
from msl.io import constants

account = 'testing'
credentials = os.path.join(constants.HOME_DIR, account + '-client-secret.json')

GMail(account=account, credentials=credentials)
GSheets(account=account, credentials=credentials, read_only=True)
GSheets(account=account, credentials=credentials, read_only=False)
GDrive(account=account, credentials=credentials, read_only=True)
GDrive(account=account, credentials=credentials, read_only=False)
