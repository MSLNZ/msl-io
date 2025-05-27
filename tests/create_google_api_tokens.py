"""Create new access tokens for the Google APIs."""

from msl.io import GDrive, GMail, GSheets, constants

account = "testing"
credentials = constants.MSL_IO_DIR / f"{account}-client-secret.json"

_ = GMail(account=account, credentials=credentials)
_ = GSheets(account=account, credentials=credentials, read_only=True)  # type: ignore[assignment]
_ = GSheets(account=account, credentials=credentials, read_only=False)  # type: ignore[assignment]
_ = GDrive(account=account, credentials=credentials, read_only=True)  # type: ignore[assignment]
_ = GDrive(account=account, credentials=credentials, read_only=False)  # type: ignore[assignment]
