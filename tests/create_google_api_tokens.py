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
    print('GSheets, is_read_only', read_only)
    GSheets(
        is_corporate_account=False,
        is_read_only=read_only,
        credentials=credentials
    )

    print('GDrive, is_read_only', read_only)
    GDrive(
        is_corporate_account=False,
        is_read_only=read_only,
        credentials=credentials
    )
