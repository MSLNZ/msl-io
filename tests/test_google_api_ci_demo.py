from __future__ import annotations

from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp

import pytest
from google.auth.exceptions import RefreshError

from msl.io.google_api import GDrive, GSheets

# all Google API tests require the necessary "token.json" file to be
# available for a specific Google user's account
drive: GDrive | None
sheet: GSheets | None
try:
    drive = GDrive(account="demo", read_only=False)
    sheet = GSheets(account="demo", read_only=False)
except (OSError, RefreshError):
    drive = None
    sheet = None


tmp_dir = Path()


def setup_module() -> None:
    global tmp_dir  # noqa: PLW0603
    tmp_dir = Path(mkdtemp(prefix="msl-io-test-"))


def teardown_module() -> None:  # cSpell: ignore teardown
    rmtree(tmp_dir)
    if sheet is not None:
        sheet.close()
    if drive is not None:
        drive.close()


@pytest.mark.skipif(drive is None, reason="No GDrive CI demo account token")
@pytest.mark.skipif(sheet is None, reason="No GSheets CI demo account token")
def test_drive_sheets() -> None:  # noqa: PLR0915
    assert sheet is not None
    assert drive is not None
    filename = Path(__file__).name
    drives = drive.shared_drives()
    drive_id = next(iter(drives))
    assert drives[drive_id] == "MSL - Joe"
    assert drive_id == "0AAkJczPd2UhCUk9PVA"
    spreadsheet_id = sheet.create("spreadsheet", sheet_names=["a"])
    spreadsheet_2_id = sheet.create("spreadsheet-2")
    assert drive.path(spreadsheet_id) == "My Drive/spreadsheet"
    files_id = drive.create_folder("Files", parent_id=drive_id)
    copy_sid = drive.copy(spreadsheet_id, files_id)
    assert drive.path(spreadsheet_id) == "My Drive/spreadsheet"
    assert drive.path(copy_sid) == "Drive/Files/Copy of spreadsheet"
    sheet.write("hi", copy_sid, "A1")
    assert sheet.values(copy_sid, "A1") == [["hi"]]
    assert drive.path(spreadsheet_2_id) == "My Drive/spreadsheet-2"
    assert sheet.sheet_names(spreadsheet_2_id) == ("Sheet1",)
    _ = sheet.copy("a", copy_sid, spreadsheet_2_id)
    assert sheet.sheet_names(spreadsheet_2_id) == ("Sheet1", "Copy of a")
    assert sheet.values(copy_sid, cells="A1", sheet="a") == [["hi"]]
    assert drive.path(files_id) == "Drive/Files"
    assert drive.folder_id("Files", parent_id=drive_id) == files_id
    assert drive.folder_id("Drive/Files", parent_id=drive_id) == files_id
    assert drive.is_folder("Files", parent_id=drive_id) is True
    assert drive.is_file(filename, folder_id=files_id) is False
    f_id = drive.upload(__file__, folder_id=files_id)
    assert drive.path(f_id) == "Drive/Files/" + filename
    assert drive.is_file(filename, folder_id=files_id) is True
    assert drive.file_id(filename, folder_id=files_id) == f_id
    help_id = drive.create_folder("help", parent_id=files_id)
    drive.move(f_id, help_id)
    assert drive.path(f_id) == "Drive/Files/help/" + filename
    assert drive.is_folder("Drive/Files/help", parent_id=drive_id) is True
    assert drive.is_folder("Files/help", parent_id=drive_id) is True
    assert drive.is_folder("help", parent_id=files_id) is True
    assert drive.is_file("Files/help/" + filename, folder_id=drive_id) is True
    assert drive.is_file("help/" + filename, folder_id=files_id) is True
    assert drive.is_file(filename, folder_id=help_id) is True
    assert drive.is_file("help/" + filename) is False
    assert not (tmp_dir / filename).is_file()
    drive.download(f_id, save_to=tmp_dir)
    assert (tmp_dir / filename).is_file()
    assert not (tmp_dir / "new.py").is_file()
    drive.download(f_id, save_to=tmp_dir / "new.py")
    assert (tmp_dir / "new.py").is_file()
    drive.move(f_id, "root")
    assert drive.path(f_id) == "My Drive/" + filename
    drive.move(f_id, files_id)
    assert drive.path(f_id) == "Drive/Files/" + filename
    iid = drive.create_folder("Files Backup")
    copy_f_id = drive.copy(f_id, iid)
    assert drive.path(copy_f_id) == "My Drive/Files Backup/" + filename
    drive.delete(files_id)
    drive.delete(iid)
    drive.delete(spreadsheet_id)
    drive.delete(spreadsheet_2_id)
    drive.empty_trash()
