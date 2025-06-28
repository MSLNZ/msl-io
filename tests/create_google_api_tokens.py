"""Create new access tokens for the Google APIs."""

from msl.io import GDrive, GMail, GSheets, constants

account = "testing"
credentials = constants.MSL_IO_DIR / f"{account}-client-secret.json"

m = GMail(account=account, credentials=credentials)
s = GSheets(account=account, credentials=credentials, read_only=True)
s = GSheets(account=account, credentials=credentials, read_only=False)
d = GDrive(account=account, credentials=credentials, read_only=True)
d = GDrive(account=account, credentials=credentials, read_only=False)
