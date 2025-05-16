"""Create new access tokens for the Google APIs."""  # noqa: INP001

from msl.io import GDrive, GMail, GSheets, constants

account = "testing"
credentials = constants.MSL_IO_DIR / f"{account}-client-secret.json"

_ = GMail(account=account, credentials=credentials)
_ = GSheets(account=account, credentials=credentials, read_only=True)
_ = GSheets(account=account, credentials=credentials, read_only=False)
_ = GDrive(account=account, credentials=credentials, read_only=True)
_ = GDrive(account=account, credentials=credentials, read_only=False)
