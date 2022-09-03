"""
Create new access tokens (for testing purposes) for the Google API.
"""
import os
os.environ['MSL_IO_RUNNING_TESTS'] = 'True'

from msl.io import (
    constants,
    GSheets,
    GDrive,
)

credentials = os.path.join(constants.HOME_DIR, 'testing-client-secret.json')


for read_only in [True, False]:
    GSheets(
        is_corporate_account=False,
        read_only=read_only,
        credentials=credentials
    )
    GDrive(
        is_corporate_account=False,
        read_only=read_only,
        credentials=credentials
    )
