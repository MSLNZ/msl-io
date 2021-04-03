"""
Wrappers around the Google API's.
"""
import os
from enum import Enum
from datetime import (
    datetime,
    timedelta,
)

from .constants import (
    HOME_DIR,
    IS_PYTHON2,
)

# the Google API packages do not work in Python 2.7
if not IS_PYTHON2:
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.http import (
        MediaFileUpload,
        MediaIoBaseDownload,
        DEFAULT_CHUNK_SIZE,
    )
else:
    DEFAULT_CHUNK_SIZE = 100 * 1024 * 1024


def _authenticate(token, client_secrets_file, scopes):
    """Authenticate with a Google API.

    Parameters
    ----------
    token : :class:`str`
        The path to a token file. If it does not exist then it will be created.
    client_secrets_file : :class:`str`
        The "client secrets" file to use to generate the OAuth credentials.
    scopes : :class:`list` of :class:`str`
        The list of scopes to enable.

    Returns
    -------
    :class:`google.oauth2.credentials.Credentials`
        The OAuth 2.0 credentials for the user.
    """
    credentials = None

    # load the cached token file if it exists
    if os.path.isfile(token):
        credentials = Credentials.from_authorized_user_file(token, scopes)

    # if there are no (valid) credentials available then let the user log in
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            if client_secrets_file is None:
                raise OSError('You must specify the path to a "client secrets" file as the credentials')
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
            credentials = flow.run_local_server(port=0)

        # make sure that all parent directories exist before creating the file
        os.makedirs(os.path.dirname(token), exist_ok=True)

        # save the credentials for the next run
        with open(token, 'w') as token:
            token.write(credentials.to_json())

    return credentials


class GoogleAPI(object):

    def __init__(self, service, version, credentials, scopes, is_read_only, is_corporate_account):
        """Base class for all Google API's."""

        if IS_PYTHON2:
            raise RuntimeError('Google API is not supported in Python 2')

        corporate = '-corporate' if is_corporate_account else ''
        readonly = '-readonly' if is_read_only else ''
        token = os.path.join(HOME_DIR, 'token-{}{}{}.json'.format(service, corporate, readonly))
        oauth = _authenticate(token, credentials, scopes)
        self._service = build(service, version, credentials=oauth)

    @property
    def service(self):
        """The Resource object with methods for interacting with the API service."""
        return self._service


class GDrive(GoogleAPI):

    MIME_TYPE_FOLDER = 'application/vnd.google-apps.folder'
    ROOT_NAMES = ['Google Drive', 'My Drive', 'Shared drives']

    def __init__(self, credentials=None, is_read_only=True, is_corporate_account=True, scopes=None):
        """Interact with a user's Google Drive.

        .. attention::
           You must follow the instructions for setting up the
           `Drive API <https://developers.google.com/drive/api/v3/quickstart/python#prerequisites>`_
           before you can use this class.

        Parameters
        ----------
        credentials : :class:`str`, optional
            The path to the "client secrets" credential file. This file only
            needs to be specified the first time that you interact with a
            user's Google Drive or if you delete the token file that was
            created when you previously authenticated using the credentials.
        is_read_only : :class:`bool`, optional
            Whether to interact with a user's Google Drive in read-only mode.
        is_corporate_account : :class:`bool`, optional
            Whether you want to interact with a user's Google Drive via a
            corporate Google account or a personal Google account.
        scopes : :class:`list` of :class:`str`, optional
            The list of scopes to enable for the Google API. See
            `Drive scopes <https://developers.google.com/identity/protocols/oauth2/scopes#drive>`_
            for more details. If not specified then default scopes are chosen
            based on the value of `is_read_only`.
        """
        if not scopes:
            if is_read_only:
                scopes = [
                    'https://www.googleapis.com/auth/drive.readonly',
                    'https://www.googleapis.com/auth/drive.metadata.readonly'
                ]
            else:
                scopes = [
                    'https://www.googleapis.com/auth/drive',
                    'https://www.googleapis.com/auth/drive.metadata',
                ]

        super(GDrive, self).__init__(
            'drive', 'v3', credentials, scopes, is_read_only, is_corporate_account
        )

        self._files = self._service.files()
        self._drives = self._service.drives()

    @staticmethod
    def _folder_hierarchy(folder):
        # create a list of sub-folder names in the folder hierarchy
        f = folder
        names = []
        while True:
            f, name = os.path.split(f)
            if not name or name in GDrive.ROOT_NAMES:
                break
            names.append(name)
        return names[::-1]

    def folder_id(self, folder):
        """Get the ID of a Google Drive folder.

        Parameters
        ----------
        folder : :class:`str`
            The path to a Google Drive file.

        Returns
        -------
        :class:`str`
            The folder ID.
        """
        # find the ID of the folder
        folder_id = 'root'
        names = GDrive._folder_hierarchy(folder)
        for name in names:
            q = '{!r} in parents and name={!r} and trashed=false and mimeType={!r}'.format(
                folder_id, name, GDrive.MIME_TYPE_FOLDER
            )
            request = self._files.list(q=q, fields='files(id,name)')
            response = request.execute()
            files = response['files']
            if not files:
                raise OSError('Not a valid Google Drive folder {!r}'.format(folder))
            if len(files) > 1:
                raise OSError('Multiple folder matches -- {}'.format(files))

            first = files[0]
            assert name == first['name'], '{!r} != {!r}'.format(name, first['name'])
            folder_id = first['id']

        return folder_id

    def file_id(self, file, mime_type=None):
        """Get the ID of a Google Drive file.

        Parameters
        ----------
        file : :class:`str`
            The path to a Google Drive file.
        mime_type : :class:`str`, optional
            The mime type to use to filter the results.

        Returns
        -------
        :class:`str`
            The file ID.
        """
        folders, name = os.path.split(file)
        folder_id = self.folder_id(folders)

        q = '{!r} in parents and name={!r} and trashed=false'.format(folder_id, name)
        if not mime_type:
            q += ' and mimeType!={!r}'.format(GDrive.MIME_TYPE_FOLDER)
        else:
            q += ' and mimeType={!r}'.format(mime_type)

        request = self._files.list(q=q, fields='files(id,name,mimeType)')
        response = request.execute()
        files = response['files']
        if not files:
            raise OSError('Not a valid Google Drive file {!r}'.format(file))
        if len(files) > 1:
            mime_types = '\n  '.join(f['mimeType'] for f in files)
            raise OSError('Multiple file matches. Filter by mime type:\n  ' + mime_types)

        first = files[0]
        assert name == first['name'], '{!r} != {!r}'.format(name, first['name'])
        return first['id']

    def is_file(self, file, mime_type=None):
        """Check if a file exists.

        Parameters
        ----------
        file : :class:`str`
            The path to a Google Drive file.
        mime_type : :class:`str`, optional
            The mime type to use to filter the results.

        Returns
        -------
        :class:`bool`
            Whether the file exists.
        """
        try:
            self.file_id(file, mime_type=mime_type)
        except OSError as err:
            return str(err).startswith('Multiple file matches')
        else:
            return True

    def is_folder(self, folder):
        """Check if a folder exists.

        Parameters
        ----------
        folder : :class:`str`
            The path to a Google Drive folder.

        Returns
        -------
        :class:`bool`
            Whether the folder exists.
        """
        try:
            self.folder_id(folder)
        except OSError:
            return False
        else:
            return True

    def create_folder(self, folder):
        """Create a folder.

        Makes all intermediate-level folders needed to contain the leaf directory.

        Parameters
        ----------
        folder : :class:`str`
            The folder(s) to create.

        Returns
        -------
        :class:`str`
            The ID of the last folder that was created.
        """
        names = GDrive._folder_hierarchy(folder)
        response = {'id': 'root'}
        for name in names:
            request = self._files.create(
                body={
                    'name': name,
                    'mimeType': GDrive.MIME_TYPE_FOLDER,
                    'parents': [response['id']],
                },
                fields='id',
                supportsAllDrives=True,  # ability to create in shared drives
            )
            response = request.execute()
        return response['id']

    def delete(self, file_or_folder_id):
        """Delete a file or a folder.

        Parameters
        ----------
        file_or_folder_id : :class:`str`
            The ID of the file or folder to delete.
        """
        self._files.delete(fileId=file_or_folder_id).execute()

    def empty_trash(self):
        """Permanently delete all of the user's trashed files."""
        self._files.emptyTrash().execute()

    def upload(self, file, folder_id=None, mime_type=None, resumable=False, chunk_size=DEFAULT_CHUNK_SIZE):
        """Upload a file.

        Parameters
        ----------
        file : :class:`str`
            The file to upload.
        folder_id : :class:`str`, optional
            The ID of the Google Drive folder to upload the file to.
            If not specified then uploads to the "root" folder.
        mime_type : :class:`str`, optional
            The mime type to use for the file's metadata. If not specified
            then a value will be guessed from the file extension.
        resumable : :class:`bool`
            Whether the upload can be resumed.
        chunk_size : :class:`int`
            The file will be uploaded in chunks of this many bytes. Only used
            if `resumable` is :data:`True`. Pass in a value of -1 if the file
            is to be uploaded in a single chunk. Note that Google App Engine
            has a 5MB limit on request size, so you should never set
            `chunk_size` to be >5MB or to -1 (if the file size is >5MB).

        Returns
        -------
        :class:`str`
            The ID of the file that was uploaded.
        """
        parent_id = folder_id or 'root'
        filename = os.path.basename(file)

        body = {'name': filename, 'parents': [parent_id]}
        if mime_type:
            body['mimeType'] = mime_type

        request = self._files.create(
            body=body,
            media_body=MediaFileUpload(
                file,
                mimetype=mime_type,
                chunksize=chunk_size,
                resumable=resumable
            ),
            fields='id',
            supportsAllDrives=True,  # ability to upload to shared drives
        )
        response = request.execute()
        return response['id']

    def download(self, file_id, save_as=None, num_retries=0, chunk_size=DEFAULT_CHUNK_SIZE, callback=None):
        """Download a file.

        Parameters
        ----------
        file_id : :class:`str`
            The ID of the file to download.
        save_as : :term:`path-like <path-like object>` or :term:`file-like <file object>`, optional
            The location to save the file to.
            Default is in the current working directory.
        num_retries : :class:`int`, optional
            The number of times to retry the download.
            If zero (default) then attempt the request only once.
        chunk_size : :class:`int`, optional
            The file will be downloaded in chunks of this many bytes.
        callback : :class:`bool`, optional
            The callback to call after each chunk of the file is downloaded.
            The `callback` accepts one positional argument, for example::

                def handler(file):
                    print(file.progress(), file.total_size, file.resumable_progress)

                drive.download('0Bwab3C2ejYSdM190b2psXy1C50P', callback=handler)

        """
        if hasattr(save_as, 'write'):
            fh = save_as
        else:
            if not save_as:
                request = self._files.get(fileId=file_id, fields='name')
                response = request.execute()
                save_as = response['name']
            fh = open(save_as, mode='wb')

        request = self._files.get_media(fileId=file_id)
        downloader = MediaIoBaseDownload(fh, request, chunksize=chunk_size)
        done = False
        while not done:
            status, done = downloader.next_chunk(num_retries=num_retries)
            if callback:
                callback(status)

        if fh is not save_as:  # then close the file that was opened
            fh.close()


class GValueOption(Enum):
    """Determines how values should be returned."""

    FORMATTED = 'FORMATTED_VALUE'
    """Values will be calculated and formatted in the reply according to the
    cell's formatting. Formatting is based on the spreadsheet's locale, not
    the requesting user's locale. For example, if A1 is 1.23 and A2 is =A1
    and formatted as currency, then A2 would return "$1.23"."""

    UNFORMATTED = 'UNFORMATTED_VALUE'
    """Values will be calculated, but not formatted in the reply.
    For example, if A1 is 1.23 and A2 is =A1 and formatted as currency, then
    A2 would return the number 1.23."""

    FORMULA = 'FORMULA'
    """Values will not be calculated. The reply will include the formulas.
    For example, if A1 is 1.23 and A2 is =A1 and formatted as currency,
    then A2 would return "=A1"."""


class GDateTimeOption(Enum):
    """Determines how dates should be returned."""

    SERIAL_NUMBER = 'SERIAL_NUMBER'
    """Instructs date, time, datetime, and duration fields to be output as
    doubles in "serial number" format, as popularized by Lotus 1-2-3. The
    whole number portion of the value (left of the decimal) counts the days
    since December 30th 1899. The fractional portion (right of the decimal)
    counts the time as a fraction of the day. For example, January 1st 1900
    at noon would be 2.5, 2 because it's 2 days after December 30st 1899,
    and .5 because noon is half a day. February 1st 1900 at 3pm would be
    33.625. This correctly treats the year 1900 as not a leap year."""

    FORMATTED_STRING = 'FORMATTED_STRING'
    """Instructs date, time, datetime, and duration fields to be output as
    strings in their given number format (which is dependent on the
    spreadsheet locale)."""


class GSheets(GoogleAPI):

    MIME_TYPE = 'application/vnd.google-apps.spreadsheet'
    LOTUS_ORIGIN = datetime(1899, 12, 30)

    def __init__(self, credentials=None, is_read_only=True, is_corporate_account=True, scopes=None):
        """Interact with a user's Google Sheets.

        .. attention::
           You must follow the instructions for setting up the
           `Sheets API <https://developers.google.com/sheets/api/quickstart/python#prerequisites>`_
           before you can use this class.

        Parameters
        ----------
        credentials : :class:`str`, optional
            The path to the "client secrets" credential file. This file only
            needs to be specified the first time that you interact with a
            user's Google Sheets or if you delete the token file that was
            created when you previously authenticated using the credentials.
        is_read_only : :class:`bool`, optional
            Whether to interact with a user's Google Sheets in read-only mode.
        is_corporate_account : :class:`bool`, optional
            Whether you want to interact with a user's Google Sheets via a
            corporate Google account or a personal Google account.
        scopes : :class:`list` of :class:`str`, optional
            The list of scopes to enable for the Google API. See
            `Sheets scopes <https://developers.google.com/identity/protocols/oauth2/scopes#sheets>`_
            for more details. If not specified then default scopes are chosen
            based on the value of `is_read_only`.
        """
        if not scopes:
            if is_read_only:
                scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
            else:
                scopes = ['https://www.googleapis.com/auth/spreadsheets']

        super(GSheets, self).__init__(
            'sheets', 'v4', credentials, scopes, is_read_only, is_corporate_account
        )

        self._sheets = self._service.spreadsheets()

    def sheet_names(self, spreadsheet_id):
        """Get the names of all sheets in a spreadsheet.

        Parameters
        ----------
        spreadsheet_id : :class:`str`
            The ID of a Google Sheets file.

        Returns
        -------
        :class:`tuple` of :class:`str`
            The names of all sheets.
        """
        request = self._sheets.get(spreadsheetId=spreadsheet_id)
        response = request.execute()
        return tuple(r['properties']['title'] for r in response['sheets'])

    def values(self,
               spreadsheet_id,
               sheet=None,
               cells=None,
               row_major=True,
               value_option=GValueOption.FORMATTED,
               datetime_option=GDateTimeOption.SERIAL_NUMBER
               ):
        """Returns a range of values from a spreadsheet.

        Parameters
        ----------
        spreadsheet_id : :class:`str`
            The ID of a Google Sheets file.
        sheet : :class:`str`, optional
            The name of a sheet in the spreadsheet. If not specified then
            automatically determines the sheet name. If more than one sheet
            exists in the spreadsheet then a :exc:`ValueError` is raised
            requesting for a `sheet` to be specified.
        cells : :class:`str`, optional
            The A1 notation or R1C1 notation of the range to retrieve values
            from. If not specified then returns all values that are in `sheet`.
        row_major : :class:`bool`, optional
            Whether to return the values in row-major or column-major order.
        value_option : :class:`str` or :class:`GValueOption`, optional
            How values should be represented in the output. If a string
            then it must be equal to one of the values in :class:`GValueOption`.
        datetime_option : :class:`str` or :class:`GDateTimeOption`, optional
            How dates, times, and durations should be represented in the
            output. If a string then it must be equal to one of the values
            in :class:`GDateTimeOption`. This argument is ignored if
            `value_option` is ``FORMATTED_VALUE``.

        Returns
        -------
        :class:`list`
            The values.
        """
        if not sheet:
            names = self.sheet_names(spreadsheet_id)
            if len(names) != 1:
                sheets = ', '.join(repr(n) for n in names)
                raise ValueError('You must specify a sheet name: ' + sheets)
            sheet = names[0]

        range_ = sheet
        if cells:
            range_ += '!{}'.format(cells)

        if hasattr(value_option, 'value'):
            value_option = value_option.value

        if hasattr(datetime_option, 'value'):
            datetime_option = datetime_option.value

        request =self._sheets.values().get(
            spreadsheetId=spreadsheet_id,
            range=range_,
            majorDimension='ROWS' if row_major else 'COLUMNS',
            valueRenderOption=value_option,
            dateTimeRenderOption=datetime_option
        )
        response = request.execute()
        return response.get('values', [])

    @staticmethod
    def lotus_to_datetime(value):
        """Convert a Lotus 1-2-3 date into a :class:`datetime.datetime`.

        Parameters
        ----------
        value : :class:`float`
            A date in the Lotus 1-2-3 format.

        Returns
        -------
        :class:`datetime.datetime`
            The date converted.
        """
        days = int(value)
        seconds = (value - days) * 86400  # 60 * 60 * 24
        return GSheets.LOTUS_ORIGIN + timedelta(days=days, seconds=seconds)
