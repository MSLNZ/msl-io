"""Wrappers around Google APIs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple, overload

# having the Google-API packages are optional
try:
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import (  # type: ignore[import-untyped]  # pyright: ignore[reportMissingTypeStubs]
        InstalledAppFlow,  # pyright: ignore[reportUnknownVariableType]
    )
    from googleapiclient.discovery import (  # type: ignore[import-untyped]  # pyright: ignore[reportMissingTypeStubs]
        build,  # pyright: ignore[reportUnknownVariableType]
    )
    from googleapiclient.errors import (  # type: ignore[import-untyped]  # pyright: ignore[reportMissingTypeStubs]
        HttpError,  # pyright: ignore[reportUnknownVariableType]
    )
    from googleapiclient.http import (  # type: ignore[import-untyped]  # pyright: ignore[reportMissingTypeStubs]
        MediaFileUpload,  # pyright: ignore[reportUnknownVariableType]
        MediaIoBaseDownload,  # pyright: ignore[reportUnknownVariableType]
    )

    has_google_api = True
except ImportError:
    has_google_api = False

from .constants import MSL_IO_DIR

if TYPE_CHECKING:
    import sys
    from collections.abc import Iterable, MutableSequence
    from io import BufferedWriter, BytesIO
    from typing import Any, Callable, Literal

    from .types import MediaDownloadProgress, PathLike

    # the Self type was added in Python 3.11 (PEP 673)
    # using TypeVar is equivalent for < 3.11
    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing import TypeVar

        Self = TypeVar("Self", bound="GoogleAPI")  # pyright: ignore[reportUnreachable]


DEFAULT_CHUNK_SIZE = 100 * 1024 * 1024


def _authenticate(token: Path, client_secrets_file: Path | None, scopes: list[str]) -> Credentials:  # noqa: C901
    """Authenticate with a Google API.

    Args:
        token: The path to a token file. If it does not exist then it will be created.
        client_secrets_file: The "client secrets" file to use to generate the OAuth credentials.
        scopes: The list of scopes to enable.

    Returns:
        The OAuth 2.0 credentials for the user.
    """
    if not has_google_api:
        msg = (
            "You must install the Google-API packages, run\n"
            "  pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
        )
        raise RuntimeError(msg)

    credentials = None

    # load the token dict from an environment variable if it exists
    # ignore the '.json' extension
    token_env_name = token.name[:-5].replace("-", "_").upper()
    if token_env_name in os.environ:
        info = json.loads(os.environ[token_env_name])
        credentials = Credentials.from_authorized_user_info(info, scopes=scopes)  # type: ignore[no-untyped-call] # pyright: ignore[reportPossiblyUnboundVariable,reportUnknownMemberType]

    # load the cached token file if it exists
    if not credentials and token.is_file():
        credentials = Credentials.from_authorized_user_file(token, scopes=scopes)  # type: ignore[no-untyped-call] # pyright: ignore[reportPossiblyUnboundVariable,reportUnknownMemberType]

    # if there are no (valid) credentials available then let the user log in
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:  # pyright: ignore[reportUnknownMemberType]
            try:
                credentials.refresh(Request())  # type: ignore[no-untyped-call] # pyright: ignore[reportUnknownMemberType,reportPossiblyUnboundVariable]
            except RefreshError as err:  # pyright: ignore[reportPossiblyUnboundVariable,reportUnknownVariableType]
                if token.is_file() and not os.getenv("MSL_IO_RUNNING_TESTS"):
                    yes_no = input(f"RefreshError: {err}\nDelete the token file and re-authenticate (y/N)? ")
                    if yes_no.lower().startswith("y"):
                        token.unlink()
                        return _authenticate(token, client_secrets_file, scopes)
                raise
        else:
            if not client_secrets_file:
                msg = "Must specify the path to a 'client secrets' file as the credentials"
                raise OSError(msg)
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)  # pyright: ignore[reportPossiblyUnboundVariable,reportUnknownVariableType,reportUnknownMemberType]
            credentials = flow.run_local_server(port=0)  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]

        # to_json() returns the result of json.dumps so it serialises the credentials as a string
        serialised: str = credentials.to_json()  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

        # save the credentials for the next run
        if token_env_name in os.environ:
            os.environ[token_env_name] = serialised
        else:
            # make sure that all parent directories exist before creating the file
            token.parent.mkdir(parents=True, exist_ok=True)
            _ = token.write_text(serialised)  # pyright: ignore[reportUnknownArgumentType]

    return credentials  # type: ignore[no-any-return] # pyright: ignore[reportUnknownVariableType]


class GoogleAPI:
    """Base class for all Google APIs."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        service: str,
        version: str,
        account: str | None,
        credentials: Path | None,
        scopes: list[str],
        read_only: bool,
    ) -> None:
        """Base class for all Google APIs."""
        name = f"{account}-" if account else ""
        readonly = "-readonly" if read_only else ""
        token = MSL_IO_DIR / f"{name}token-{service}{readonly}.json"
        oauth = _authenticate(token, credentials, scopes)
        self._service: Any = build(service, version, credentials=oauth)  # pyright: ignore[reportPossiblyUnboundVariable]

    def __enter__(self: Self) -> Self:  # noqa: PYI019
        """Enter a context manager."""
        return self

    def __exit__(self, *ignore: object) -> None:
        """Exit the context manager."""
        self.close()

    @property
    def service(self) -> Any:
        """The Resource object with methods for interacting with the API service."""
        return self._service

    def close(self) -> None:
        """Close the connection to the API service."""
        self._service.close()


class GDrive(GoogleAPI):
    """Interact with Google Drive."""

    MIME_TYPE_FOLDER: str = "application/vnd.google-apps.folder"
    ROOT_NAMES: tuple[str, ...] = ("Google Drive", "My Drive", "Drive")

    def __init__(
        self,
        *,
        account: str | None = None,
        credentials: PathLike | None = None,
        scopes: list[str] | None = None,
        read_only: bool = True,
    ) -> None:
        """Interact with Google Drive.

        !!! attention
            You must follow the instructions in the prerequisites section for setting up the
            [Drive API](https://developers.google.com/drive/api/quickstart/python#prerequisites)
            before you can use this class. It is also useful to be aware of the
            [refresh token expiration](https://developers.google.com/identity/protocols/oauth2#expiration)
            policy.

        [Media type]: https://www.iana.org/assignments/media-types/media-types.xhtml
        [Drive MIME type]: https://developers.google.com/drive/api/guides/mime-types

        Args:
            account: Since a person may have multiple Google accounts, and multiple people
                may run the same code, this parameter decides which token to load to authenticate
                with the Google API. The value can be any text (or `None`) that you want to
                associate with a particular Google account, provided that it contains valid
                characters for a filename. The value that you chose when you authenticated with
                your `credentials` should be used for all future instances of this class to access
                that particular Google account. You can associate a different value with a Google
                account at any time (by passing in a different `account` value), but you will be
                asked to authenticate with your `credentials` again, or, alternatively, you can
                rename the token files located in [MSL_IO_DIR][msl.io.constants.MSL_IO_DIR]
                to match the new `account` value.
            credentials: The path to the `client secrets` OAuth credential file. This parameter only
                needs to be specified the first time that you authenticate with a particular Google
                `account` or if you delete the token file that was created when you previously authenticated.
            scopes: The list of scopes to enable for the Google API. See
                [Drive scopes](https://developers.google.com/identity/protocols/oauth2/scopes#drive)
                for more details. If not specified, default scopes are chosen based on the value of `read_only`.
            read_only: Whether to interact with Google Drive in read-only mode.
        """
        if not scopes:
            if read_only:
                scopes = [
                    "https://www.googleapis.com/auth/drive.readonly",
                    "https://www.googleapis.com/auth/drive.metadata.readonly",
                ]
            else:
                scopes = [
                    "https://www.googleapis.com/auth/drive",
                    "https://www.googleapis.com/auth/drive.metadata",
                ]

        c = Path(os.fsdecode(credentials)) if credentials else None
        super().__init__(
            service="drive", version="v3", account=account, credentials=c, scopes=scopes, read_only=read_only
        )

        self._files: Any = self._service.files()
        self._drives: Any = self._service.drives()

    @staticmethod
    def _folder_hierarchy(folder: PathLike) -> list[str]:
        # create a list of sub-folder names in the folder hierarchy
        f = os.fsdecode(folder)
        names: list[str] = []
        while True:
            f, name = os.path.split(f)
            if not name or name in GDrive.ROOT_NAMES:
                break
            names.append(name)
        return names[::-1]

    def folder_id(self, folder: PathLike, *, parent_id: str | None = None) -> str:
        """Get the ID of a Google Drive folder.

        Args:
            folder: The path to a Google Drive file.
            parent_id: The ID of the parent folder that `folder` is relative to. If not
                specified, `folder` is relative to the `My Drive` root folder. If `folder`
                is in a `Shared drive` then you must specify the ID of the parent folder.

        Returns:
            The folder ID.
        """
        folder_id = parent_id or "root"
        folder = os.fsdecode(folder)
        names = GDrive._folder_hierarchy(folder)
        for name in names:
            q = f'"{folder_id}" in parents and name="{name}" and trashed=false and mimeType="{GDrive.MIME_TYPE_FOLDER}"'
            response = self._files.list(
                q=q,
                fields="files(id,name)",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            ).execute()
            files = response["files"]
            if not files:
                msg = f"Not a valid Google Drive folder {folder!r}"
                raise OSError(msg)
            if len(files) > 1:
                matches = "\n  ".join(str(file) for file in files)
                msg = f"Multiple folders exist for {name!r}\n  {matches}"
                raise OSError(msg)

            first = files[0]
            assert name == first["name"], f"{name!r} != {first['name']!r}"  # noqa: S101
            folder_id = first["id"]

        return folder_id

    def file_id(self, file: PathLike, *, mime_type: str | None = None, folder_id: str | None = None) -> str:
        """Get the ID of a Google Drive file.

        Args:
            file: The path to a Google Drive file.
            mime_type: The [Drive MIME type] or [Media type] to use to filter the results.
            folder_id: The ID of the folder that `file` is relative to. If not specified, `file`
                is relative to the `My Drive` root folder. If `file` is in a `Shared drive` then
                you must specify the ID of the parent folder.

        [Media type]: https://www.iana.org/assignments/media-types/media-types.xhtml
        [Drive MIME type]: https://developers.google.com/drive/api/guides/mime-types

        Returns:
            The file ID.
        """
        folders, name = os.path.split(os.fsdecode(file))
        folder_id = self.folder_id(folders, parent_id=folder_id)

        q = f'"{folder_id}" in parents and name="{name}" and trashed=false'
        if not mime_type:
            q += f' and mimeType!="{GDrive.MIME_TYPE_FOLDER}"'
        else:
            q += f' and mimeType="{mime_type}"'

        response = self._files.list(
            q=q,
            fields="files(id,name,mimeType)",
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
        ).execute()
        files = response["files"]
        if not files:
            msg = f"Not a valid Google Drive file {file!r}"
            raise OSError(msg)
        if len(files) > 1:
            mime_types = "\n  ".join(f["mimeType"] for f in files)
            msg = f"Multiple files exist for {file!r}. Filter by MIME type:\n  {mime_types}"
            raise OSError(msg)

        first = files[0]
        assert name == first["name"], "{name!r} != {first['name']!r}"  # noqa: S101
        return str(first["id"])

    def is_file(self, file: PathLike, *, mime_type: str | None = None, folder_id: str | None = None) -> bool:
        """Check if a file exists.

        Args:
            file: The path to a Google Drive file.
            mime_type: The [Drive MIME type] or [Media type] to use to filter the results.
            folder_id: The ID of the folder that `file` is relative to. If not specified, `file`
                is relative to the `My Drive` root folder. If `file` is in a `Shared drive` then
                you must specify the ID of the parent folder.

        [Media type]: https://www.iana.org/assignments/media-types/media-types.xhtml
        [Drive MIME type]: https://developers.google.com/drive/api/guides/mime-types

        Returns:
            Whether the file exists.
        """
        try:
            _ = self.file_id(file, mime_type=mime_type, folder_id=folder_id)
        except OSError as err:
            return str(err).startswith("Multiple files")
        else:
            return True

    def is_folder(self, folder: PathLike, parent_id: str | None = None) -> bool:
        """Check if a folder exists.

        Args:
            folder: The path to a Google Drive folder.
            parent_id: The ID of the parent folder that `folder` is relative to. If not
                specified, `folder` is relative to the `My Drive` root folder. If `folder`
                is in a `Shared drive` then you must specify the ID of the parent folder.

        Returns:
            Whether the folder exists.
        """
        try:
            _ = self.folder_id(folder, parent_id=parent_id)
        except OSError as err:
            return str(err).startswith("Multiple folders")
        else:
            return True

    def create_folder(self, folder: PathLike, parent_id: str | None = None) -> str:
        """Create a folder.

        Makes all intermediate-level folders needed to contain the leaf directory.

        Args:
            folder: The folder(s) to create, for example, `'folder1'` or `'folder1/folder2/folder3'`.
            parent_id: The ID of the parent folder that `folder` is relative to. If not
                specified, `folder` is relative to the `My Drive` root folder. If `folder`
                is in a `Shared drive` then you must specify the ID of the parent folder.

        Returns:
            The ID of the last (right most) folder that was created.
        """
        names = GDrive._folder_hierarchy(folder)
        response = {"id": parent_id or "root"}
        for name in names:
            request = self._files.create(
                body={
                    "name": name,
                    "mimeType": GDrive.MIME_TYPE_FOLDER,
                    "parents": [response["id"]],
                },
                fields="id",
                supportsAllDrives=True,
            )
            response = request.execute()
        return response["id"]

    def delete(self, file_or_folder_id: str) -> None:
        """Delete a file or a folder.

        Files that are in read-only mode cannot be deleted.

        !!! caution
            Permanently deletes the file or folder owned by the user without
            moving it to the trash. If the target is a folder, then all files
            and sub-folders contained within the folder (that are owned by the
            user) are also permanently deleted.

        Args:
            file_or_folder_id: The ID of the file or folder to delete.
        """
        if self.is_read_only(file_or_folder_id):
            # The API allows for a file to be deleted if it is in read-only mode,
            # but we will not allow it to be deleted
            msg = "Cannot delete the file since it is in read-only mode"
            raise RuntimeError(msg)

        self._files.delete(
            fileId=file_or_folder_id,
            supportsAllDrives=True,
        ).execute()

    def empty_trash(self) -> None:
        """Permanently delete all files in the trash."""
        self._files.emptyTrash().execute()

    def upload(
        self,
        file: PathLike,
        *,
        folder_id: str | None = None,
        mime_type: str | None = None,
        resumable: bool = False,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> str:
        """Upload a file.

        Args:
            file: The file to upload.
            folder_id: The ID of the folder to upload the file to. If not specified,
                uploads to the `My Drive` root folder.
            mime_type: The [Drive MIME type] or [Media type] of the file (e.g., `'text/csv'`).
                If not specified then a type will be guessed based on the file extension.
            resumable: Whether the upload can be resumed.
            chunk_size: The file will be uploaded in chunks of this many bytes. Only used
                if `resumable` is `True`. Specify a value of -1 if the file is to be uploaded
                in a single chunk. Note that Google App Engine has a 5MB limit per request size,
                so you should not set `chunk_size` to be &gt; 5MB or to -1 if the file size is &gt; 5MB.

        [Media type]: https://www.iana.org/assignments/media-types/media-types.xhtml
        [Drive MIME type]: https://developers.google.com/drive/api/guides/mime-types

        Returns:
            The ID of the file that was uploaded.
        """
        parent_id = folder_id or "root"
        file = os.fsdecode(file)
        filename = Path(file).name

        body = {"name": filename, "parents": [parent_id]}
        if mime_type:
            body["mimeType"] = mime_type

        request = self._files.create(
            body=body,
            media_body=MediaFileUpload(file, mimetype=mime_type, chunksize=chunk_size, resumable=resumable),  # pyright: ignore[reportPossiblyUnboundVariable]
            fields="id",
            supportsAllDrives=True,
        )
        response = request.execute()
        return str(response["id"])

    def download(
        self,
        file_id: str,
        *,
        save_to: PathLike | BufferedWriter | BytesIO | None = None,
        num_retries: int = 0,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        callback: Callable[[MediaDownloadProgress], None] | None = None,
    ) -> None:
        """Download a file.

        Args:
            file_id: The ID of the file to download.
            save_to: The location to save the file to. If a directory is specified, the directory
                must already exist and the file will be saved to that directory using the filename
                of the remote file. To save the file with a new filename, also specify the new filename.
                Default is to save the file to the current working directory using the remote filename.
            num_retries: The number of times to retry the download.
                If zero (default) then attempt the request only once.
            chunk_size: The file will be downloaded in chunks of this many bytes.
            callback: The callback function to call after each chunk of the file is downloaded.
                The `callback` accepts one positional argument, for example

                ```python
                def handler(file):
                    print(file.progress(), file.total_size, file.resumable_progress)

                drive.download('0cWab3C2ejYSdM190b2psXy1C50P', callback=handler)
                ```
        """
        response = self._files.get(
            fileId=file_id,
            fields="name",
            supportsAllDrives=True,
        ).execute()
        filename: str = response["name"]

        file: BufferedWriter | BytesIO
        if save_to is None:
            file = Path(filename).open("wb")  # noqa: SIM115
        elif isinstance(save_to, (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(save_to))
            file = (path / filename).open("wb") if path.is_dir() else path.open("wb")
        else:
            file = save_to

        request = self._files.get_media(fileId=file_id, supportsAllDrives=True)
        downloader = MediaIoBaseDownload(file, request, chunksize=chunk_size)  # pyright: ignore[reportPossiblyUnboundVariable,reportUnknownVariableType]
        done = False
        while not done:
            status, done = downloader.next_chunk(num_retries=num_retries)  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
            if callback:
                callback(status)  # pyright: ignore[reportUnknownArgumentType]

        if file is not save_to:
            file.close()

    def path(self, file_or_folder_id: str) -> str:
        """Convert an ID to a path.

        Args:
            file_or_folder_id: The ID of a file or folder.

        Returns:
            The corresponding path of the ID.
        """
        names: list[str] = []
        while True:
            request = self._files.get(
                fileId=file_or_folder_id,
                fields="name,parents",
                supportsAllDrives=True,
            )
            response = request.execute()
            names.append(response["name"])
            parents = response.get("parents", [])
            if not parents:
                break
            if len(parents) > 1:
                msg = "Multiple parents exist. This case has not been handled yet. Contact developers."
                raise OSError(msg)
            file_or_folder_id = response["parents"][0]
        return "/".join(names[::-1])

    def move(self, source_id: str, destination_id: str) -> None:
        """Move a file or a folder.

        When moving a file or folder between `My Drive` and a `Shared drive`
        the access permissions will change.

        Moving a file or folder does not change its ID, only the ID of
        its `parent` changes (i.e., `source_id` will remain the same
        after the move).

        Args:
            source_id: The ID of a file or folder to move.
            destination_id: The ID of the destination folder. To move the file or folder to the
                `My Drive` root folder then specify `'root'` as the `destination_id`.
        """
        params = {"fileId": source_id, "supportsAllDrives": True}
        try:
            self._files.update(addParents=destination_id, **params).execute()
        except HttpError as e:  # pyright: ignore[reportPossiblyUnboundVariable,reportUnknownVariableType]
            if "exactly one parent" not in str(e):  # pyright: ignore[reportUnknownArgumentType]
                raise

            # Handle the following error:
            #   A shared drive item must have exactly one parent
            response = self._files.get(fields="parents", **params).execute()
            self._files.update(
                addParents=destination_id, removeParents=",".join(response["parents"]), **params
            ).execute()

    def shared_drives(self) -> dict[str, str]:
        """Returns the IDs and names of all `Shared drives`.

        Returns:
            The keys are the IDs of the shared drives and the values are the names of the shared drives.
        """
        drives: dict[str, str] = {}
        next_page_token = ""
        while True:
            response = self._drives.list(pageSize=100, pageToken=next_page_token).execute()
            drives.update({d["id"]: d["name"] for d in response["drives"]})
            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break
        return drives

    def copy(self, file_id: str, folder_id: str | None = None, name: str | None = None) -> str:
        """Copy a file.

        Args:
            file_id: The ID of a file to copy. Folders cannot be copied.
            folder_id: The ID of the destination folder. If not specified then creates
                a copy in the same folder that the original file is located in. To copy
                the file to the `My Drive` root folder then specify `'root'` as the `folder_id`.
            name: The filename of the destination file.

        Returns:
            The ID of the destination file.
        """
        response = self._files.copy(
            fileId=file_id,
            fields="id",
            supportsAllDrives=True,
            body={
                "name": name,
                "parents": [folder_id] if folder_id else None,
            },
        ).execute()
        return str(response["id"])

    def rename(self, file_or_folder_id: str, new_name: str) -> None:
        """Rename a file or folder.

        Renaming a file or folder does not change its ID.

        Args:
            file_or_folder_id: The ID of a file or folder.
            new_name: The new name of the file or folder.
        """
        self._files.update(
            fileId=file_or_folder_id,
            supportsAllDrives=True,
            body={"name": new_name},
        ).execute()

    def read_only(self, file_id: str, read_only: bool, reason: str | None = None) -> None:  # noqa: FBT001
        """Set a file to be in read-only mode.

        Args:
            file_id: The ID of a file.
            read_only: Whether to set the file to be in read-only mode.
            reason: The reason for putting the file in read-only mode.
                Only used if `read_only` is `True`.
        """
        restrictions: dict[str, bool | str] = {"readOnly": read_only}
        if read_only:
            restrictions["reason"] = reason or ""

            # If `file_id` is already in read-only mode, and it is being set
            # to read-only mode then the API raises a TimeoutError waiting for
            # a response. To avoid this error, check the mode and if it is
            # already in read-only mode we are done.
            if self.is_read_only(file_id):
                return

        self._files.update(
            fileId=file_id, supportsAllDrives=True, body={"contentRestrictions": [restrictions]}
        ).execute()

    def is_read_only(self, file_or_folder_id: str) -> bool:
        """Returns whether the file or folder is accessed in read-only mode.

        Args:
            file_or_folder_id: The ID of a file or folder.

        Returns:
            Whether the file or folder is accessed in read-only mode.
        """
        response = self._files.get(
            fileId=file_or_folder_id,
            supportsAllDrives=True,
            fields="contentRestrictions",
        ).execute()
        restrictions = response.get("contentRestrictions")
        if not restrictions:
            return False
        r: bool = restrictions[0]["readOnly"]
        return r


class GValueOption(Enum):
    """Determines how values should be returned."""

    FORMATTED = "FORMATTED_VALUE"
    """Values will be calculated and formatted in the reply according to the
    cell's formatting. Formatting is based on the spreadsheet's locale, not
    the requesting user's locale. For example, if A1 is 1.23 and A2 is =A1
    and formatted as currency, then A2 would return "$1.23"."""

    UNFORMATTED = "UNFORMATTED_VALUE"
    """Values will be calculated, but not formatted in the reply.
    For example, if A1 is 1.23 and A2 is =A1 and formatted as currency, then
    A2 would return the number 1.23."""

    FORMULA = "FORMULA"
    """Values will not be calculated. The reply will include the formulas.
    For example, if A1 is 1.23 and A2 is =A1 and formatted as currency,
    then A2 would return "=A1"."""


class GDateTimeOption(Enum):
    """Determines how dates should be returned."""

    SERIAL_NUMBER = "SERIAL_NUMBER"
    """Instructs date, time, datetime, and duration fields to be output as
    doubles in "serial number" format, as popularized by Lotus 1-2-3. The
    whole number portion of the value (left of the decimal) counts the days
    since December 30th 1899. The fractional portion (right of the decimal)
    counts the time as a fraction of the day. For example, January 1st 1900
    at noon would be 2.5, 2 because it's 2 days after December 30st 1899,
    and .5 because noon is half a day. February 1st 1900 at 3pm would be
    33.625. This correctly treats the year 1900 as not a leap year."""

    FORMATTED_STRING = "FORMATTED_STRING"
    """Instructs date, time, datetime, and duration fields to be output as
    strings in their given number format (which is dependent on the
    spreadsheet locale)."""


class GCellType(Enum):
    """The spreadsheet cell data type.

    Attributes:
        BOOLEAN (str): `"BOOLEAN"`
        CURRENCY (str): `"CURRENCY"`
        DATE (str): `"DATE"`
        DATE_TIME (str): `"DATE_TIME"`
        EMPTY (str): `"EMPTY"`
        ERROR (str): `"ERROR"`
        NUMBER (str): `"NUMBER"`
        PERCENT (str): `"PERCENT"`
        SCIENTIFIC (str): `"SCIENTIFIC"`
        STRING (str): `"STRING"`
        TEXT (str): `"TEXT"`
        TIME (str): `"TIME"`
        UNKNOWN (str): `"UNKNOWN"`
    """

    BOOLEAN = "BOOLEAN"
    CURRENCY = "CURRENCY"
    DATE = "DATE"
    DATE_TIME = "DATE_TIME"
    EMPTY = "EMPTY"
    ERROR = "ERROR"
    NUMBER = "NUMBER"
    PERCENT = "PERCENT"
    SCIENTIFIC = "SCIENTIFIC"
    STRING = "STRING"
    TEXT = "TEXT"
    TIME = "TIME"
    UNKNOWN = "UNKNOWN"


class GCell(NamedTuple):
    """The information about a Google Sheets cell.

    Attributes:
        value ([Any][typing.Any]): The value of the cell.
        type ([GCellType][]): The data type of `value`.
        formatted ([str][]): The formatted value (i.e., how the `value` is displayed in the cell).
    """

    value: Any
    type: GCellType
    formatted: str


class GSheets(GoogleAPI):
    """Interact with Google Sheets."""

    MIME_TYPE: str = "application/vnd.google-apps.spreadsheet"
    SERIAL_NUMBER_ORIGIN: datetime = datetime(1899, 12, 30)  # noqa: DTZ001

    def __init__(
        self,
        *,
        account: str | None = None,
        credentials: PathLike | None = None,
        scopes: list[str] | None = None,
        read_only: bool = True,
    ) -> None:
        """Interact with Google Sheets.

        !!! attention
            You must follow the instructions in the prerequisites section for setting up the
            [Sheets API](https://developers.google.com/sheets/api/quickstart/python#prerequisites)
            before you can use this class. It is also useful to be aware of the
            [refresh token expiration](https://developers.google.com/identity/protocols/oauth2#expiration)
            policy.

        Args:
            account: Since a person may have multiple Google accounts, and multiple people
                may run the same code, this parameter decides which token to load
                to authenticate with the Google API. The value can be any text (or
                `None`) that you want to associate with a particular Google
                account, provided that it contains valid characters for a filename.
                The value that you chose when you authenticated with your `credentials`
                should be used for all future instances of this class to access that
                particular Google account. You can associate a different value with
                a Google account at any time (by passing in a different `account`
                value), but you will be asked to authenticate with your `credentials`
                again, or, alternatively, you can rename the token files located in
                [MSL_IO_DIR][msl.io.constants.MSL_IO_DIR]` to match the new `account` value.
            credentials: The path to the `client secrets` OAuth credential file. This
                parameter only needs to be specified the first time that you
                authenticate with a particular Google account or if you delete
                the token file that was created when you previously authenticated.
            scopes: The list of scopes to enable for the Google API. See
                [Sheets scopes](https://developers.google.com/identity/protocols/oauth2/scopes#sheets)
                for more details. If not specified, default scopes are chosen based on the value of `read_only`.
            read_only: Whether to interact with Google Sheets in read-only mode.
        """
        if not scopes:
            if read_only:
                scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
            else:
                scopes = ["https://www.googleapis.com/auth/spreadsheets"]

        c = Path(os.fsdecode(credentials)) if credentials else None
        super().__init__(
            service="sheets", version="v4", account=account, credentials=c, scopes=scopes, read_only=read_only
        )

        self._spreadsheets: Any = self._service.spreadsheets()

    def append(  # noqa: PLR0913
        self,
        values: Any | list[Any] | tuple[Any, ...] | list[list[Any]] | tuple[tuple[Any, ...], ...],
        spreadsheet_id: str,
        cell: str | None = None,
        sheet: str | None = None,
        *,
        row_major: bool = True,
        raw: bool = False,
    ) -> None:
        """Append values to a sheet.

        Args:
            values: The value(s) to append
            spreadsheet_id: The ID of a Google Sheets file.
            cell: The cell (top-left corner) to start appending the values to. If the
                cell already contains data then new rows are inserted and the values
                are written to the new rows. For example, `'D100'`.
            sheet: The name of a sheet in the spreadsheet to append the values to.
                If not specified and only one sheet exists in the spreadsheet
                then automatically determines the sheet name; however, it is
                more efficient to specify the name of the sheet.
            row_major: Whether to append the values in row-major or column-major order.
            raw: Determines how the values should be interpreted. If `True`,
                the values will not be parsed and will be stored as-is. If
                `False`, the values will be parsed as if the user typed
                them into the UI. Numbers will stay as numbers, but strings may
                be converted to numbers, dates, etc. following the same rules
                that are applied when entering text into a cell via the Google
                Sheets UI.
        """
        self._spreadsheets.values().append(
            spreadsheetId=spreadsheet_id,
            range=self._get_range(sheet, cell, spreadsheet_id),
            valueInputOption="RAW" if raw else "USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={
                "values": self._values(values),
                "majorDimension": "ROWS" if row_major else "COLUMNS",
            },
        ).execute()

    def write(  # noqa: PLR0913
        self,
        values: Any | list[Any] | tuple[Any, ...] | list[list[Any]] | tuple[tuple[Any, ...], ...],
        spreadsheet_id: str,
        cell: str | None = None,
        sheet: str | None = None,
        *,
        row_major: bool = True,
        raw: bool = False,
    ) -> None:
        """Write values to a sheet.

        If a cell that is being written to already contains a value,
        the value in that cell is overwritten with the new value.

        Args:
            values: The value(s) to write.
            spreadsheet_id: The ID of a Google Sheets file.
            cell: The cell (top-left corner) to start writing the values to. For example, `'C9'`.
            sheet: The name of a sheet in the spreadsheet to write the values to.
                If not specified and only one sheet exists in the spreadsheet
                then automatically determines the sheet name; however, it is
                more efficient to specify the name of the sheet.
            row_major: Whether to write the values in row-major or column-major order.
            raw: Determines how the values should be interpreted. If `True`,
                the values will not be parsed and will be stored as-is. If
                `False`, the values will be parsed as if the user typed
                them into the UI. Numbers will stay as numbers, but strings may
                be converted to numbers, dates, etc. following the same rules
                that are applied when entering text into a cell via the Google
                Sheets UI.
        """
        self._spreadsheets.values().update(
            spreadsheetId=spreadsheet_id,
            range=self._get_range(sheet, cell, spreadsheet_id),
            valueInputOption="RAW" if raw else "USER_ENTERED",
            body={
                "values": self._values(values),
                "majorDimension": "ROWS" if row_major else "COLUMNS",
            },
        ).execute()

    def copy(self, name_or_id: str | int, spreadsheet_id: str, destination_spreadsheet_id: str) -> int:
        """Copy a sheet from one spreadsheet to another spreadsheet.

        Args:
            name_or_id: The name or ID of the sheet to copy.
            spreadsheet_id: The ID of the spreadsheet that contains the sheet.
            destination_spreadsheet_id: The ID of a spreadsheet to copy the sheet to.

        Returns:
            The ID of the sheet in the destination spreadsheet.
        """
        sheet_id = name_or_id if isinstance(name_or_id, int) else self.sheet_id(name_or_id, spreadsheet_id)

        response = (
            self._spreadsheets.sheets()
            .copyTo(
                spreadsheetId=spreadsheet_id,
                sheetId=sheet_id,
                body={
                    "destination_spreadsheet_id": destination_spreadsheet_id,
                },
            )
            .execute()
        )
        return int(response["sheetId"])

    def sheet_id(self, name: str, spreadsheet_id: str) -> int:
        """Returns the ID of a sheet.

        Args:
            name: The name of the sheet.
            spreadsheet_id: The ID of the spreadsheet.

        Returns:
            The ID of the sheet.
        """
        request = self._spreadsheets.get(spreadsheetId=spreadsheet_id)
        response = request.execute()
        for sheet in response["sheets"]:
            if sheet["properties"]["title"] == name:
                return int(sheet["properties"]["sheetId"])

        msg = f"There is no sheet named {name!r}"
        raise ValueError(msg)

    def rename_sheet(self, name_or_id: str | int, new_name: str, spreadsheet_id: str) -> None:
        """Rename a sheet.

        Args:
            name_or_id: The name or ID of the sheet to rename.
            new_name: The new name of the sheet.
            spreadsheet_id: The ID of the spreadsheet that contains the sheet.
        """
        sheet_id = name_or_id if isinstance(name_or_id, int) else self.sheet_id(name_or_id, spreadsheet_id)

        self._spreadsheets.batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": [
                    {
                        "updateSheetProperties": {
                            "properties": {
                                "sheetId": sheet_id,
                                "title": new_name,
                            },
                            "fields": "title",
                        }
                    }
                ]
            },
        ).execute()

    def add_sheets(self, names: str | Iterable[str], spreadsheet_id: str) -> dict[int, str]:
        """Add sheets to a spreadsheet.

        Args:
            names: The name(s) of the new sheet(s) to add.
            spreadsheet_id: The ID of the spreadsheet to add the sheet(s) to.

        Returns:
            The keys are the IDs of the new sheets and the values are the names.
        """
        if isinstance(names, str):
            names = [names]

        response = self._spreadsheets.batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": name}}} for name in names]},
        ).execute()

        return {
            r["addSheet"]["properties"]["sheetId"]: r["addSheet"]["properties"]["title"] for r in response["replies"]
        }

    def delete_sheets(self, names_or_ids: str | int | Iterable[str | int], spreadsheet_id: str) -> None:
        """Delete sheets from a spreadsheet.

        Args:
            names_or_ids: The name(s) or ID(s) of the sheet(s) to delete.
            spreadsheet_id: The ID of the spreadsheet to delete the sheet(s) from.
        """
        if isinstance(names_or_ids, (str, int)):
            names_or_ids = [names_or_ids]

        self._spreadsheets.batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": [
                    {"deleteSheet": {"sheetId": n if isinstance(n, int) else self.sheet_id(n, spreadsheet_id)}}
                    for n in names_or_ids
                ]
            },
        ).execute()

    def create(self, name: str, sheet_names: Iterable[str] | None = None) -> str:
        """Create a new spreadsheet.

        The spreadsheet will be created in the `My Drive` root folder.
        To move it to a different folder use [GDrive.create_folder][msl.io.google_api.GDrive.create_folder]
        and/or [GDrive.move][msl.io.google_api.GDrive.move].

        Args:
            name: The name of the spreadsheet.
            sheet_names: The names of the sheets that will be in the new spreadsheet.

        Returns:
            The ID of the spreadsheet that was created.
        """
        body: dict[str, dict[str, str] | list[dict[str, dict[str, str]]]] = {"properties": {"title": name}}
        if sheet_names:
            body["sheets"] = [{"properties": {"title": sn}} for sn in sheet_names]
        response = self._spreadsheets.create(body=body).execute()
        return str(response["spreadsheetId"])

    def sheet_names(self, spreadsheet_id: str) -> tuple[str, ...]:
        """Get the names of all sheets in a spreadsheet.

        Args:
            spreadsheet_id: The ID of a Google Sheets file.

        Returns:
            The names of all sheets.
        """
        request = self._spreadsheets.get(spreadsheetId=spreadsheet_id)
        response = request.execute()
        return tuple(r["properties"]["title"] for r in response["sheets"])

    def values(  # noqa: PLR0913
        self,
        spreadsheet_id: str,
        sheet: str | None = None,
        cells: str | None = None,
        *,
        row_major: bool = True,
        value_option: str | GValueOption = GValueOption.FORMATTED,
        datetime_option: str | GDateTimeOption = GDateTimeOption.SERIAL_NUMBER,
    ) -> list[list[Any]]:
        """Return a range of values from a spreadsheet.

        Args:
            spreadsheet_id: The ID of a Google Sheets file.
            sheet: The name of a sheet in the spreadsheet to read the values from.
                If not specified and only one sheet exists in the spreadsheet
                then automatically determines the sheet name; however, it is
                more efficient to specify the name of the sheet.
            cells: The `A1` notation or `R1C1` notation of the range to retrieve values
                from. If not specified then returns all values that are in `sheet`.
            row_major: Whether to return the values in row-major or column-major order.
            value_option: How values should be represented in the output. If a [str][],
                it must be equal to one of the values in [GValueOption][msl.io.google_api.GValueOption].
            datetime_option: How dates, times, and durations should be represented in the
                output. If a [str][], it must be equal to one of the values in
                [GDateTimeOption][msl.io.google_api.GDateTimeOption]. This argument is ignored if `value_option` is
                [GValueOption.FORMATTED][msl.io.google_api.GValueOption.FORMATTED].

        Returns:
        -------
            The values from the sheet.
        """
        if isinstance(value_option, GValueOption):
            value_option = value_option.value

        if isinstance(datetime_option, GDateTimeOption):
            datetime_option = datetime_option.value

        response = (
            self._spreadsheets.values()
            .get(
                spreadsheetId=spreadsheet_id,
                range=self._get_range(sheet, cells, spreadsheet_id),
                majorDimension="ROWS" if row_major else "COLUMNS",
                valueRenderOption=value_option,
                dateTimeRenderOption=datetime_option,
            )
            .execute()
        )
        return response.get("values", [[]])  # type: ignore[no-any-return]

    def cells(self, spreadsheet_id: str, ranges: str | list[str] | None = None) -> dict[str, list[list[GCell]]]:  # noqa: C901
        """Return cells from a spreadsheet.

        Args:
            spreadsheet_id: The ID of a Google Sheets file.
            ranges: The ranges to retrieve from the spreadsheet. If not specified then return all cells
                from all sheets. For example,
                * `'Sheet1'` &#8594; Return all cells from the sheet named `Sheet1`
                * `'Sheet1!A1:H5'` &#8594; Return cells `A1:H5` from the sheet named `Sheet1`
                * `['Sheet1!A1:H5', 'Data', 'Devices!B4:B9']` &#8594; Return cells `A1:H5`
                    from the sheet named `Sheet1`, all cells from the sheet named `Data`
                    and cells `B4:B9` from the sheet named Devices

        Returns:
            The cells from the spreadsheet. The keys are the names of the sheets.
        """
        response = self._spreadsheets.get(
            spreadsheetId=spreadsheet_id,
            includeGridData=True,
            ranges=ranges,
        ).execute()
        cells: dict[str, list[list[GCell]]] = {}
        for sheet in response["sheets"]:
            data: list[list[GCell]] = []
            for item in sheet["data"]:
                for row in item.get("rowData", []):
                    row_data: list[GCell] = []
                    for col in row.get("values", []):
                        effective_value = col.get("effectiveValue", None)
                        formatted = col.get("formattedValue", "")
                        if effective_value is None:
                            value = None
                            typ = GCellType.EMPTY
                        elif "numberValue" in effective_value:
                            value = effective_value["numberValue"]
                            t = col.get("effectiveFormat", {}).get("numberFormat", {}).get("type", "NUMBER")
                            try:
                                typ = GCellType(t)
                            except ValueError:
                                typ = GCellType.UNKNOWN
                        elif "stringValue" in effective_value:
                            value = effective_value["stringValue"]
                            typ = GCellType.STRING
                        elif "boolValue" in effective_value:
                            value = effective_value["boolValue"]
                            typ = GCellType.BOOLEAN
                        elif "errorValue" in effective_value:
                            msg = effective_value["errorValue"]["message"]
                            value = "{} ({})".format(col["formattedValue"], msg)
                            typ = GCellType.ERROR
                        else:
                            value = formatted
                            typ = GCellType.UNKNOWN
                        row_data.append(GCell(value=value, type=typ, formatted=formatted))
                    data.append(row_data)
                cells[sheet["properties"]["title"]] = data
        return cells

    @staticmethod
    def to_datetime(value: float) -> datetime:
        """Convert a "serial number" date into a [datetime.datetime][].

        Args:
            value: A date in the "serial number" format.

        Returns:
            The date converted.
        """
        days = int(value)
        seconds = (value - days) * 86400  # 60 * 60 * 24
        return GSheets.SERIAL_NUMBER_ORIGIN + timedelta(days=days, seconds=seconds)

    def _get_range(self, sheet: str | None, cells: str | None, spreadsheet_id: str) -> str:
        if not sheet:
            names = self.sheet_names(spreadsheet_id)
            if len(names) != 1:
                sheets = ", ".join(repr(n) for n in names)
                raise ValueError("You must specify a sheet name: " + sheets)
            _range = names[0]
        else:
            _range = sheet

        if cells:
            _range += f"!{cells}"

        return _range

    @staticmethod
    def _values(values: Any | list[Any] | tuple[Any, ...] | list[list[Any]] | tuple[tuple[Any, ...], ...]) -> Any:
        """The append() and update() API methods require a list of lists."""
        if not isinstance(values, (list, tuple)):
            return [[values]]
        if values and not isinstance(values[0], (list, tuple)):
            return [values]
        return values  # pyright: ignore[reportUnknownVariableType]


@dataclass
class Profile:
    """An authenticated user's Gmail profile.

    Attributes:
        email_address (str): The authenticated user's email address
        messages_total (int): The total number of messages in the mailbox
        threads_total (int): The total number of threads in the mailbox
        history_id (str): The ID of the mailbox's current history record
    """

    email_address: str
    messages_total: int
    threads_total: int
    history_id: str

    @overload
    def __getitem__(self, item: Literal["email_address"]) -> str: ...

    @overload
    def __getitem__(self, item: Literal["messages_total"]) -> int: ...

    @overload
    def __getitem__(self, item: Literal["threads_total"]) -> int: ...

    @overload
    def __getitem__(self, item: Literal["history_id"]) -> str: ...

    def __getitem__(self, item: str) -> str | int:
        """Gmail.profile() used to return a dict, treat the dataclass like a read-only dict."""
        value: str | int = getattr(self, item)
        return value


class GMail(GoogleAPI):
    """Interact with Gmail."""

    def __init__(
        self,
        account: str | None = None,
        credentials: PathLike | None = None,
        scopes: list[str] | None = None,
    ) -> None:
        """Interact with Gmail.

        !!! attention
            You must follow the instructions in the prerequisites section for setting up the
            [Gmail API](https://developers.google.com/gmail/api/quickstart/python#prerequisites)
            before you can use this class. It is also useful to be aware of the
            [refresh token expiration](https://developers.google.com/identity/protocols/oauth2#expiration)
            policy.

        Args:
            account: Since a person may have multiple Google accounts, and multiple people
                may run the same code, this parameter decides which token to load to
                authenticate with the Google API. The value can be any text (or `None`)
                that you want to associate with a particular Google account, provided that
                it contains valid characters for a filename. The value that you chose when
                you authenticated with your `credentials` should be used for all future
                instances of this class to access that particular Google account. You can
                associate a different value with a Google account at any time (by passing
                in a different `account` value), but you will be asked to authenticate with
                your `credentials` again, or, alternatively, you can rename the token files
                located in [MSL_IO_DIR][msl.io.constants.MSL_IO_DIR] to match the new
                `account` value.
            credentials: The path to the `client secrets` OAuth credential file. This
                parameter only needs to be specified the first time that you
                authenticate with a particular Google account or if you delete
                the token file that was created when you previously authenticated.
            scopes: The list of scopes to enable for the Google API. See
                [Gmail scopes](https://developers.google.com/identity/protocols/oauth2/scopes#gmail)
                for more details. If not specified then default scopes are chosen.
        """
        if not scopes:
            scopes = ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.metadata"]

        c = Path(os.fsdecode(credentials)) if credentials else None
        super().__init__(service="gmail", version="v1", account=account, credentials=c, scopes=scopes, read_only=False)

        self._my_email_address: str | None = None
        self._users: Any = self._service.users()

    def profile(self) -> Profile:
        """Gets the authenticated user's Gmail profile.

        Returns:
            The current users GMAIL profile.
        """
        profile = self._users.getProfile(userId="me").execute()
        return Profile(
            email_address=str(profile["emailAddress"]),
            messages_total=int(profile["messagesTotal"]),
            threads_total=int(profile["threadsTotal"]),
            history_id=str(profile["historyId"]),
        )

    def send(
        self,
        recipients: str | MutableSequence[str],
        sender: str = "me",
        subject: str | None = None,
        body: str | None = None,
    ) -> None:
        """Send an email.

        !!! note "See also [send_email][msl.io.utils.send_email]".

        Args:
            recipients: The email address(es) of the recipient(s). The value `'me'` can be used
                to indicate the authenticated user.
            sender: The email address of the sender. The value `'me'` can be used to indicate
                the authenticated user.
            subject: The text to include in the subject field.
            body: The text to include in the body of the email. The text can be enclosed in
                `<html></html>` tags to use HTML elements to format the message.
        """
        from base64 import b64encode  # noqa: PLC0415
        from email.mime.multipart import MIMEMultipart  # noqa: PLC0415
        from email.mime.text import MIMEText  # noqa: PLC0415

        if isinstance(recipients, str):
            recipients = [recipients]

        for i in range(len(recipients)):
            if recipients[i] == "me":
                if self._my_email_address is None:
                    self._my_email_address = str(self.profile()["email_address"])
                recipients[i] = self._my_email_address

        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject or "(no subject)"

        text = body or ""
        subtype = "html" if text.startswith("<html>") else "plain"
        msg.attach(MIMEText(text, subtype))

        self._users.messages().send(userId=sender, body={"raw": b64encode(msg.as_bytes()).decode()}).execute()
