"""
Wrappers around Google APIs.
"""
import json
import os
from base64 import b64encode
from collections import OrderedDict
from collections import namedtuple
from datetime import datetime
from datetime import timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    # this is only an issue with Python 2.7 and if the
    # Google-API packages were not installed with msl-io
    from enum import Enum
except ImportError:
    Enum = object

# having the Google-API packages are optional
try:
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import DEFAULT_CHUNK_SIZE
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.http import MediaIoBaseDownload
    HAS_GOOGLE_API = True
except ImportError:
    DEFAULT_CHUNK_SIZE = 100 * 1024 * 1024
    HAS_GOOGLE_API = False

from .constants import HOME_DIR
from .constants import IS_PYTHON2


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
    if not HAS_GOOGLE_API:
        raise RuntimeError(
            'You must install the Google-API packages, run\n'
            '  pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib'
        )

    credentials = None

    # load the token from an environment variable if it exists
    # ignore the '.json' extension
    token_env_name = os.path.basename(token)[:-5].replace('-', '_').upper()
    if token_env_name in os.environ:
        info = json.loads(os.environ[token_env_name])
        credentials = Credentials.from_authorized_user_info(info, scopes=scopes)

    # load the cached token file if it exists
    if not credentials and os.path.isfile(token):
        credentials = Credentials.from_authorized_user_file(token, scopes=scopes)

    # if there are no (valid) credentials available then let the user log in
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
            except RefreshError as err:
                if os.path.isfile(token) and not os.getenv('MSL_IO_RUNNING_TESTS'):
                    message = '{}: {}\nDo you want to delete the token file and re-authenticate ' \
                              '(y/N)? '.format(err.__class__.__name__, err.args[0])
                    if IS_PYTHON2:
                        yes_no = raw_input(message)
                    else:
                        yes_no = input(message)
                    if yes_no.lower().startswith('y'):
                        os.remove(token)
                        return _authenticate(token, client_secrets_file, scopes)
                raise
        else:
            if not client_secrets_file:
                raise OSError('You must specify the path to a "client secrets" file as the credentials')
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
            credentials = flow.run_local_server(port=0)

        # save the credentials for the next run
        if token_env_name in os.environ:
            os.environ[token_env_name] = credentials.to_json()
        else:
            # make sure that all parent directories exist before creating the file
            dirname = os.path.dirname(token)
            if dirname and not os.path.isdir(dirname):
                os.makedirs(dirname)
            with open(token, mode='wt') as fp:
                fp.write(credentials.to_json())

    return credentials


class GoogleAPI(object):

    def __init__(self, service, version, credentials, scopes, read_only, account):
        """Base class for all Google APIs."""

        name = '{}-'.format(account) if account else ''
        readonly = '-readonly' if read_only else ''
        filename = '{}token-{}{}.json'.format(name, service, readonly)
        token = os.path.join(HOME_DIR, filename)
        oauth = _authenticate(token, credentials, scopes)
        self._service = build(service, version, credentials=oauth)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def service(self):
        """The Resource object with methods for interacting with the API service."""
        return self._service

    def close(self):
        """Close the connection to the API service."""
        self._service.close()


class GDrive(GoogleAPI):

    MIME_TYPE_FOLDER = 'application/vnd.google-apps.folder'
    ROOT_NAMES = ['Google Drive', 'My Drive', 'Drive']

    def __init__(self, account=None, credentials=None, read_only=True, scopes=None):
        """Interact with Google Drive.

        .. attention::
           You must follow the instructions in the prerequisites section for setting up the
           `Drive API <https://developers.google.com/drive/api/quickstart/python#prerequisites>`_
           before you can use this class. It is also useful to be aware of the
           `refresh token expiration <https://developers.google.com/identity/protocols/oauth2#expiration>`_
           policy.

        .. _Media type: https://www.iana.org/assignments/media-types/media-types.xhtml
        .. _Drive MIME type: https://developers.google.com/drive/api/guides/mime-types

        Parameters
        ----------
        account : :class:`str`, optional
            Since a person may have multiple Google accounts, and multiple people
            may run the same code, this parameter decides which token to load
            to authenticate with the Google API. The value can be any text (or
            :data:`None`) that you want to associate with a particular Google
            account, provided that it contains valid characters for a filename.
            The value that you chose when you authenticated with your `credentials`
            should be used for all future instances of this class to access that
            particular Google account. You can associate a different value with
            a Google account at any time (by passing in a different `account`
            value), but you will be asked to authenticate with your `credentials`
            again, or, alternatively, you can rename the token files located in
            :const:`~msl.io.constants.HOME_DIR` to match the new `account` value.
        credentials : :class:`str`, optional
            The path to the `client secrets` OAuth credential file. This
            parameter only needs to be specified the first time that you
            authenticate with a particular Google account or if you delete
            the token file that was created when you previously authenticated.
        read_only : :class:`bool`, optional
            Whether to interact with Google Drive in read-only mode.
        scopes : :class:`list` of :class:`str`, optional
            The list of scopes to enable for the Google API. See
            `Drive scopes <https://developers.google.com/identity/protocols/oauth2/scopes#drive>`_
            for more details. If not specified then default scopes are chosen
            based on the value of `read_only`.
        """
        if not scopes:
            if read_only:
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
            'drive', 'v3', credentials, scopes, read_only, account)

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

    def folder_id(self, folder, parent_id=None):
        """Get the ID of a Google Drive folder.

        Parameters
        ----------
        folder : :class:`str`
            The path to a Google Drive file.
        parent_id : :class:`str`, optional
            The ID of the parent folder that `folder` is relative to. If not
            specified then `folder` is relative to the `My Drive` root folder.
            If `folder` is in a `Shared drive` then you must specify the
            ID of a parent folder.

        Returns
        -------
        :class:`str`
            The folder ID.
        """
        folder_id = parent_id or 'root'
        names = GDrive._folder_hierarchy(folder)
        for name in names:
            q = '"{}" in parents and name="{}" and trashed=false and mimeType="{}"'.format(
                folder_id, name, GDrive.MIME_TYPE_FOLDER
            )
            response = self._files.list(
                q=q,
                fields='files(id,name)',
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            ).execute()
            files = response['files']
            if not files:
                raise OSError('Not a valid Google Drive folder {!r}'.format(folder))
            if len(files) > 1:
                matches = '\n  '.join(str(file) for file in files)
                raise OSError('Multiple folders exist for {!r}\n  {}'.format(name, matches))

            first = files[0]
            assert name == first['name'], '{!r} != {!r}'.format(name, first['name'])
            folder_id = first['id']

        return folder_id

    def file_id(self, file, mime_type=None, folder_id=None):
        """Get the ID of a Google Drive file.

        Parameters
        ----------
        file : :class:`str`
            The path to a Google Drive file.
        mime_type : :class:`str`, optional
            The `Drive MIME type`_ or `Media type`_ to use to filter the results.
        folder_id : :class:`str`, optional
            The ID of the folder that `file` is relative to. If not specified
            then `file` is relative to the `My Drive` root folder.
            If `file` is in a `Shared drive` then you must specify the
            ID of a parent folder.

        Returns
        -------
        :class:`str`
            The file ID.
        """
        folders, name = os.path.split(file)
        folder_id = self.folder_id(folders, parent_id=folder_id)

        q = '"{}" in parents and name="{}" and trashed=false'.format(folder_id, name)
        if not mime_type:
            q += ' and mimeType!="{}"'.format(GDrive.MIME_TYPE_FOLDER)
        else:
            q += ' and mimeType="{}"'.format(mime_type)

        response = self._files.list(
            q=q,
            fields='files(id,name,mimeType)',
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
        ).execute()
        files = response['files']
        if not files:
            raise OSError('Not a valid Google Drive file {!r}'.format(file))
        if len(files) > 1:
            mime_types = '\n  '.join(f['mimeType'] for f in files)
            raise OSError('Multiple files exist for {!r}. '
                          'Filter by MIME type:\n  {}'.format(file, mime_types))

        first = files[0]
        assert name == first['name'], '{!r} != {!r}'.format(name, first['name'])
        return first['id']

    def is_file(self, file, mime_type=None, folder_id=None):
        """Check if a file exists.

        Parameters
        ----------
        file : :class:`str`
            The path to a Google Drive file.
        mime_type : :class:`str`, optional
            The `Drive MIME type`_ or `Media type`_ to use to filter the results.
        folder_id : :class:`str`, optional
            The ID of the folder that `file` is relative to. If not specified
            then `file` is relative to the `My Drive` root folder.
            If `file` is in a `Shared drive` then you must specify the
            ID of a parent folder.

        Returns
        -------
        :class:`bool`
            Whether the file exists.
        """
        try:
            self.file_id(file, mime_type=mime_type, folder_id=folder_id)
        except OSError as err:
            return str(err).startswith('Multiple files')
        else:
            return True

    def is_folder(self, folder, parent_id=None):
        """Check if a folder exists.

        Parameters
        ----------
        folder : :class:`str`
            The path to a Google Drive folder.
        parent_id : :class:`str`, optional
            The ID of the parent folder that `folder` is relative to. If not
            specified then `folder` is relative to the `My Drive` root folder.
            If `folder` is in a `Shared drive` then you must specify the
            ID of a parent folder.

        Returns
        -------
        :class:`bool`
            Whether the folder exists.
        """
        try:
            self.folder_id(folder, parent_id=parent_id)
        except OSError as err:
            return str(err).startswith('Multiple folders')
        else:
            return True

    def create_folder(self, folder, parent_id=None):
        """Create a folder.

        Makes all intermediate-level folders needed to contain the leaf directory.

        Parameters
        ----------
        folder : :class:`str`
            The folder(s) to create, for example, ``'folder1'`` or
            ``'folder1/folder2/folder3'``.
        parent_id : :class:`str`, optional
            The ID of the parent folder that `folder` is relative to. If not
            specified then `folder` is relative to the `My Drive` root folder.
            If `folder` is in a `Shared drive` then you must specify the
            ID of a parent folder.

        Returns
        -------
        :class:`str`
            The ID of the last (right most) folder that was created.
        """
        names = GDrive._folder_hierarchy(folder)
        response = {'id': parent_id or 'root'}
        for name in names:
            request = self._files.create(
                body={
                    'name': name,
                    'mimeType': GDrive.MIME_TYPE_FOLDER,
                    'parents': [response['id']],
                },
                fields='id',
                supportsAllDrives=True,
            )
            response = request.execute()
        return response['id']

    def delete(self, file_or_folder_id):
        """Delete a file or a folder.

        Files that are in read-only mode cannot be deleted.

        .. danger::
           Permanently deletes the file or folder owned by the user without
           moving it to the trash. If the target is a folder, then all files
           and sub-folders contained within the folder (that are owned by the
           user) are also permanently deleted.

        Parameters
        ----------
        file_or_folder_id : :class:`str`
            The ID of the file or folder to delete.
        """
        if self.is_read_only(file_or_folder_id):
            # The API allows for a file to be deleted if it is in read-only mode,
            # but we will not allow it to be deleted
            raise RuntimeError('Cannot delete the file since it is in read-only mode')

        self._files.delete(
            fileId=file_or_folder_id,
            supportsAllDrives=True,
        ).execute()

    def empty_trash(self):
        """Permanently delete all files in the trash."""
        self._files.emptyTrash().execute()

    def upload(self, file, folder_id=None, mime_type=None, resumable=False, chunk_size=DEFAULT_CHUNK_SIZE):
        """Upload a file.

        Parameters
        ----------
        file : :class:`str`
            The file to upload.
        folder_id : :class:`str`, optional
            The ID of the folder to upload the file to. If not specified then
            uploads to the `My Drive` root folder.
        mime_type : :class:`str`, optional
            The `Drive MIME type`_ or `Media type`_ of the file
            (e.g., ``'text/csv'``). If not specified then a type will be
            guessed based on the file extension.
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
            supportsAllDrives=True,
        )
        response = request.execute()
        return response['id']

    def download(self, file_id, save_to=None, num_retries=0, chunk_size=DEFAULT_CHUNK_SIZE, callback=None):
        """Download a file.

        Parameters
        ----------
        file_id : :class:`str`
            The ID of the file to download.
        save_to : :term:`path-like <path-like object>` or :term:`file-like <file object>`, optional
            The location to save the file to. If a directory is specified
            then the file will be saved to that directory using the filename
            of the remote file. To save the file with a new filename, specify
            the new filename in `save_to`. Default is to save the file to the
            current working directory using the remote filename.
        num_retries : :class:`int`, optional
            The number of times to retry the download.
            If zero (default) then attempt the request only once.
        chunk_size : :class:`int`, optional
            The file will be downloaded in chunks of this many bytes.
        callback
            The callback to call after each chunk of the file is downloaded.
            The `callback` accepts one positional argument, for example::

                def handler(file):
                    print(file.progress(), file.total_size, file.resumable_progress)

                drive.download('0Bwab3C2ejYSdM190b2psXy1C50P', callback=handler)

        """
        if hasattr(save_to, 'write'):
            fh = save_to
        else:
            if not save_to or os.path.isdir(save_to):
                response = self._files.get(
                    fileId=file_id,
                    fields='name',
                    supportsAllDrives=True,
                ).execute()
                name = response['name']
                if save_to and os.path.isdir(save_to):
                    save_to = os.path.join(save_to, name)
                else:
                    save_to = name
            fh = open(save_to, mode='wb')

        request = self._files.get_media(fileId=file_id, supportsAllDrives=True)
        downloader = MediaIoBaseDownload(fh, request, chunksize=chunk_size)
        done = False
        while not done:
            status, done = downloader.next_chunk(num_retries=num_retries)
            if callback:
                callback(status)

        if fh is not save_to:  # then close the file that was opened
            fh.close()

    def path(self, file_or_folder_id):
        """Convert an ID to a path.

        Parameters
        ----------
        file_or_folder_id : :class:`str`
            The ID of a file or folder.

        Returns
        -------
        :class:`str`
            The corresponding path of the ID.
        """
        names = []
        while True:
            request = self._files.get(
                fileId=file_or_folder_id,
                fields='name,parents',
                supportsAllDrives=True,
            )
            response = request.execute()
            names.append(response['name'])
            parents = response.get('parents', [])
            if not parents:
                break
            if len(parents) > 1:
                raise OSError('Multiple parents exist. This case has not been handled yet. Contact developers.')
            file_or_folder_id = response['parents'][0]
        return '/'.join(names[::-1])

    def move(self, source_id, destination_id):
        """Move a file or a folder.

        When moving a file or folder between `My Drive` and a `Shared drive`
        the access permissions will change.

        Moving a file or folder does not change its ID, only the ID of
        its `parent` changes (i.e., `source_id` will remain the same
        after the move).

        Parameters
        ----------
        source_id : :class:`str`
            The ID of a file or folder to move.
        destination_id : :class:`str`
            The ID of the destination folder. To move the file or folder to the
            `My Drive` root folder then specify ``'root'`` as the `destination_id`.
        """
        params = {'fileId': source_id, 'supportsAllDrives': True}
        try:
            self._files.update(addParents=destination_id, **params).execute()
        except HttpError as e:
            if 'exactly one parent' not in str(e):
                raise

            # Handle the following error:
            #   A shared drive item must have exactly one parent
            response = self._files.get(fields='parents', **params).execute()
            self._files.update(
                addParents=destination_id,
                removeParents=','.join(response['parents']),
                **params).execute()

    def shared_drives(self):
        """Returns the IDs and names of all `Shared drives`.

        Returns
        -------
        :class:`dict`
            The keys are the IDs of the shared drives and the values are the
            names of the shared drives.
        """
        drives = {}
        next_page_token = ''
        while True:
            response = self._drives.list(pageSize=100, pageToken=next_page_token).execute()
            drives.update(dict((d['id'], d['name']) for d in response['drives']))
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
        return drives

    def copy(self, file_id, folder_id=None, name=None):
        """Copy a file.

        Parameters
        ----------
        file_id : :class:`str`
            The ID of a file to copy. Folders cannot be copied.
        folder_id : :class:`str`, optional
            The ID of the destination folder. If not specified then creates
            a copy in the same folder that the original file is located in.
            To copy the file to the `My Drive` root folder then specify
            ``'root'`` as the `folder_id`.
        name : :class:`str`, optional
            The filename of the destination file.

        Returns
        -------
        :class:`str`
            The ID of the destination file.
        """
        response = self._files.copy(
            fileId=file_id,
            fields='id',
            supportsAllDrives=True,
            body={
                'name': name,
                'parents': [folder_id] if folder_id else None,
            },
        ).execute()
        return response['id']

    def rename(self, file_or_folder_id, new_name):
        """Rename a file or folder.

        Renaming a file or folder does not change its ID.

        Parameters
        ----------
        file_or_folder_id : :class:`str`
            The ID of a file or folder.
        new_name : :class:`str`
            The new name of the file or folder.
        """
        self._files.update(
            fileId=file_or_folder_id,
            supportsAllDrives=True,
            body={'name': new_name},
        ).execute()

    def read_only(self, file_id, read_only, reason=''):
        """Set a file to be in read-only mode.

        Parameters
        ----------
        file_id : :class:`str`
            The ID of a file.
        read_only : :class:`bool`
            Whether to set the file to be in read-only mode.
        reason : :class:`str`, optional
            The reason for putting the file in read-only mode.
            Only used if `read_only` is :data:`True`.
        """
        restrictions = {'readOnly': read_only}
        if read_only:
            restrictions['reason'] = reason

            # If `file_id` is already in read-only mode, and it is being set
            # to read-only mode then the API raises a TimeoutError waiting for
            # a response. To avoid this error, check the mode and if it is
            # already in read-only mode we are done.
            if self.is_read_only(file_id):
                return

        self._files.update(
            fileId=file_id,
            supportsAllDrives=True,
            body={'contentRestrictions': [restrictions]}
        ).execute()

    def is_read_only(self, file_id):
        """Returns whether the file is in read-only mode.

        Parameters
        ----------
        file_id : :class:`str`
            The ID of a file.

        Returns
        -------
        :class:`bool`
            Whether the file is in read-only mode.
        """
        response = self._files.get(
            fileId=file_id,
            supportsAllDrives=True,
            fields='contentRestrictions',
        ).execute()
        restrictions = response.get('contentRestrictions')
        if not restrictions:
            return False
        return restrictions[0]['readOnly']


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


class GCellType(Enum):
    """The spreadsheet cell data type."""

    BOOLEAN = 'BOOLEAN'
    CURRENCY = 'CURRENCY'
    DATE = 'DATE'
    DATE_TIME = 'DATE_TIME'
    EMPTY = 'EMPTY'
    ERROR = 'ERROR'
    NUMBER = 'NUMBER'
    PERCENT = 'PERCENT'
    SCIENTIFIC = 'SCIENTIFIC'
    STRING = 'STRING'
    TEXT = 'TEXT'
    TIME = 'TIME'
    UNKNOWN = 'UNKNOWN'


GCell = namedtuple('GCell', ('value', 'type', 'formatted'))
"""The information about a Google Sheets cell.

.. attribute:: value
   
   The value of the cell.
   
.. attribute:: type
   
   :class:`GCellType`: The data type of `value`.

.. attribute:: formatted
   
   :class:`str`: The formatted value (i.e., how the `value` is displayed in the cell).
"""


class GSheets(GoogleAPI):

    MIME_TYPE = 'application/vnd.google-apps.spreadsheet'
    SERIAL_NUMBER_ORIGIN = datetime(1899, 12, 30)

    def __init__(self, account=None, credentials=None, read_only=True, scopes=None):
        """Interact with Google Sheets.

        .. attention::
           You must follow the instructions in the prerequisites section for setting up the
           `Sheets API <https://developers.google.com/sheets/api/quickstart/python#prerequisites>`_
           before you can use this class. It is also useful to be aware of the
           `refresh token expiration <https://developers.google.com/identity/protocols/oauth2#expiration>`_
           policy.

        Parameters
        ----------
        account : :class:`str`, optional
            Since a person may have multiple Google accounts, and multiple people
            may run the same code, this parameter decides which token to load
            to authenticate with the Google API. The value can be any text (or
            :data:`None`) that you want to associate with a particular Google
            account, provided that it contains valid characters for a filename.
            The value that you chose when you authenticated with your `credentials`
            should be used for all future instances of this class to access that
            particular Google account. You can associate a different value with
            a Google account at any time (by passing in a different `account`
            value), but you will be asked to authenticate with your `credentials`
            again, or, alternatively, you can rename the token files located in
            :const:`~msl.io.constants.HOME_DIR` to match the new `account` value.
        credentials : :class:`str`, optional
            The path to the `client secrets` OAuth credential file. This
            parameter only needs to be specified the first time that you
            authenticate with a particular Google account or if you delete
            the token file that was created when you previously authenticated.
        read_only : :class:`bool`, optional
            Whether to interact with Google Sheets in read-only mode.
        scopes : :class:`list` of :class:`str`, optional
            The list of scopes to enable for the Google API. See
            `Sheets scopes <https://developers.google.com/identity/protocols/oauth2/scopes#sheets>`_
            for more details. If not specified then default scopes are chosen
            based on the value of `read_only`.
        """
        if not scopes:
            if read_only:
                scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
            else:
                scopes = ['https://www.googleapis.com/auth/spreadsheets']

        super(GSheets, self).__init__(
            'sheets', 'v4', credentials, scopes, read_only, account)

        self._spreadsheets = self._service.spreadsheets()

    def append(self, values, spreadsheet_id, cell=None, sheet=None, row_major=True, raw=False):
        """Append values to a sheet.

        Returns
        -------
        values
            The value(s) to append
        spreadsheet_id : :class:`str`
            The ID of a Google Sheets file.
        cell : :class:`str`, optional
            The cell (top-left corner) to start appending the values to. If the
            cell already contains data then new rows are inserted and the values
            are written to the new rows. For example, ``'D100'``.
        sheet : :class:`str`, optional
            The name of a sheet in the spreadsheet to append the values to.
            If not specified and only one sheet exists in the spreadsheet
            then automatically determines the sheet name; however, it is
            more efficient to specify the name of the sheet.
        row_major : :class:`bool`, optional
            Whether to append the values in row-major or column-major order.
        raw : :class:`bool`, optional
            Determines how the values should be interpreted. If :data:`True`,
            the values will not be parsed and will be stored as-is. If
            :data:`False`, the values will be parsed as if the user typed
            them into the UI. Numbers will stay as numbers, but strings may
            be converted to numbers, dates, etc. following the same rules
            that are applied when entering text into a cell via the Google
            Sheets UI.
        """
        self._spreadsheets.values().append(
            spreadsheetId=spreadsheet_id,
            range=self._get_range(sheet, cell, spreadsheet_id),
            valueInputOption='RAW' if raw else 'USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body={
                'values': self._values(values),
                'majorDimension': 'ROWS' if row_major else 'COLUMNS',
            },
        ).execute()

    def write(self, values, spreadsheet_id, cell, sheet=None, row_major=True, raw=False):
        """Write values to a sheet.

        If a cell that is being written to already contains a value,
        the value in that cell is overwritten with the new value.

        Returns
        -------
        values
            The value(s) to write.
        spreadsheet_id : :class:`str`
            The ID of a Google Sheets file.
        cell : :class:`str`, optional
            The cell (top-left corner) to start writing the values to.
            For example, ``'C9'``.
        sheet : :class:`str`, optional
            The name of a sheet in the spreadsheet to write the values to.
            If not specified and only one sheet exists in the spreadsheet
            then automatically determines the sheet name; however, it is
            more efficient to specify the name of the sheet.
        row_major : :class:`bool`, optional
            Whether to write the values in row-major or column-major order.
        raw : :class:`bool`, optional
            Determines how the values should be interpreted. If :data:`True`,
            the values will not be parsed and will be stored as-is. If
            :data:`False`, the values will be parsed as if the user typed
            them into the UI. Numbers will stay as numbers, but strings may
            be converted to numbers, dates, etc. following the same rules
            that are applied when entering text into a cell via the Google
            Sheets UI.
        """
        self._spreadsheets.values().update(
            spreadsheetId=spreadsheet_id,
            range=self._get_range(sheet, cell, spreadsheet_id),
            valueInputOption='RAW' if raw else 'USER_ENTERED',
            body={
                'values': self._values(values),
                'majorDimension': 'ROWS' if row_major else 'COLUMNS',
            },
        ).execute()

    def copy(self, name_or_id, spreadsheet_id, destination_spreadsheet_id):
        """Copy a sheet from one spreadsheet to another spreadsheet.

        Parameters
        ----------
        name_or_id : :class:`str` or :class:`int`
            The name or ID of the sheet to copy.
        spreadsheet_id : :class:`str`
            The ID of the spreadsheet that contains the sheet.
        destination_spreadsheet_id : :class:`str`
            The ID of a spreadsheet to copy the sheet to.

        Returns
        -------
        :class:`int`
            The ID of the sheet in the destination spreadsheet.
        """
        if isinstance(name_or_id, int):
            sheet_id = name_or_id
        else:
            sheet_id = self.sheet_id(name_or_id, spreadsheet_id)

        response = self._spreadsheets.sheets().copyTo(
            spreadsheetId=spreadsheet_id,
            sheetId=sheet_id,
            body={
                'destination_spreadsheet_id': destination_spreadsheet_id,
            },
        ).execute()
        return response['sheetId']

    def sheet_id(self, name, spreadsheet_id):
        """Returns the ID of a sheet.

        Parameters
        ----------
        name : :class:`str`
            The name of the sheet.
        spreadsheet_id : :class:`str`
            The ID of the spreadsheet.

        Returns
        -------
        :class:`int`
            The ID of the sheet.
        """
        request = self._spreadsheets.get(spreadsheetId=spreadsheet_id)
        response = request.execute()
        for sheet in response['sheets']:
            if sheet['properties']['title'] == name:
                return sheet['properties']['sheetId']
        raise ValueError('There is no sheet named {!r}'.format(name))

    def rename_sheet(self, name_or_id, new_name, spreadsheet_id):
        """Rename a sheet.

        Parameters
        ----------
        name_or_id : :class:`str` or :class:`int`
            The name or ID of the sheet to rename.
        new_name : :class:`str`
            The new name of the sheet.
        spreadsheet_id : :class:`str`
            The ID of the spreadsheet that contains the sheet.
        """
        if isinstance(name_or_id, int):
            sheet_id = name_or_id
        else:
            sheet_id = self.sheet_id(name_or_id, spreadsheet_id)

        self._spreadsheets.batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                'requests': [{
                    'updateSheetProperties': {
                        'properties': {
                            'sheetId': sheet_id,
                            'title': new_name,
                        },
                        'fields': 'title',
                    }
                }]
            }
        ).execute()

    def add_sheets(self, names, spreadsheet_id):
        """Add sheets to a spreadsheet.

        Parameters
        ----------
        names : :class:`str` or :class:`list` of :class:`str`
            The name(s) of the new sheet(s) to add.
        spreadsheet_id : :class:`str`
            The ID of the spreadsheet to add the sheet(s) to.

        Returns
        -------
        :class:`dict`
            The keys are the IDs of the new sheets and the values are the names.
        """
        if isinstance(names, str):
            names = [names]
        response = self._spreadsheets.batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': name
                        }
                    }
                } for name in names]
            }
        ).execute()
        return OrderedDict((r['addSheet']['properties']['sheetId'],
                            r['addSheet']['properties']['title'])
                           for r in response['replies'])

    def delete_sheets(self, names_or_ids, spreadsheet_id):
        """Delete sheets from a spreadsheet.

        Parameters
        ----------
        names_or_ids : :class:`str`, :class:`int` or :class:`list`
            The name(s) or ID(s) of the sheet(s) to delete.
        spreadsheet_id : :class:`str`
            The ID of the spreadsheet to delete the sheet(s) from.
        """
        if not isinstance(names_or_ids, (list, tuple)):
            names_or_ids = [names_or_ids]
        self._spreadsheets.batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                'requests': [{
                    'deleteSheet': {
                        'sheetId': n if isinstance(n, int) else self.sheet_id(n, spreadsheet_id)
                    }
                } for n in names_or_ids]
            }
        ).execute()

    def create(self, name, sheet_names=None):
        """Create a new spreadsheet.

        The spreadsheet will be created in the `My Drive` root folder.
        To move it to a different folder use :meth:`GDrive.create_folder`
        and/or :meth:`GDrive.move`.

        Parameters
        ----------
        name : :class:`str`
            The name of the spreadsheet.
        sheet_names : :class:`list` of :class:`str`, optional
            The names of the sheets that are in the spreadsheet.

        Returns
        -------
        :class:`str`
            The ID of the spreadsheet that was created.
        """
        body = {'properties': {'title': name}}
        if sheet_names:
            body['sheets'] = [{
                'properties': {'title': sn}
            } for sn in sheet_names]
        response = self._spreadsheets.create(body=body).execute()
        return response['spreadsheetId']

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
        request = self._spreadsheets.get(spreadsheetId=spreadsheet_id)
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
        """Return a range of values from a spreadsheet.

        Parameters
        ----------
        spreadsheet_id : :class:`str`
            The ID of a Google Sheets file.
        sheet : :class:`str`, optional
            The name of a sheet in the spreadsheet to read the values from.
            If not specified and only one sheet exists in the spreadsheet
            then automatically determines the sheet name; however, it is
            more efficient to specify the name of the sheet.
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
            `value_option` is :attr:`GValueOption.FORMATTED`.

        Returns
        -------
        :class:`list`
            The values from the sheet.
        """
        if hasattr(value_option, 'value'):
            value_option = value_option.value

        if hasattr(datetime_option, 'value'):
            datetime_option = datetime_option.value

        response = self._spreadsheets.values().get(
            spreadsheetId=spreadsheet_id,
            range=self._get_range(sheet, cells, spreadsheet_id),
            majorDimension='ROWS' if row_major else 'COLUMNS',
            valueRenderOption=value_option,
            dateTimeRenderOption=datetime_option
        ).execute()
        return response.get('values', [])

    def cells(self, spreadsheet_id, ranges=None):
        """Return cells from a spreadsheet.

        Parameters
        ----------
        spreadsheet_id : :class:`str`
            The ID of a Google Sheets file.
        ranges : :class:`str` or :class:`list` of :class:`str`, optional
            The ranges to retrieve from the spreadsheet. Examples:

                * ``'Sheet1'`` :math:`\\rightarrow` return all cells from
                  the sheet named Sheet1
                * ``'Sheet1!A1:H5'`` :math:`\\rightarrow` return cells A1:H5
                  from the sheet named Sheet1
                * ``['Sheet1!A1:H5', 'Data', 'Devices!B4:B9']`` :math:`\\rightarrow`
                  return cells A1:H5 from the sheet named Sheet1, all cells from the
                  sheet named Data and cells B4:B9 from the sheet named Devices

            If not specified then return all cells from all sheets.

        Returns
        -------
        :class:`dict`
            The cells from the spreadsheet. The keys are the names of the
            sheets and the values are a :class:`list` of :class:`GCell`
            objects for the specified range of each sheet.
        """
        response = self._spreadsheets.get(
            spreadsheetId=spreadsheet_id,
            includeGridData=True,
            ranges=ranges,
        ).execute()
        cells = {}
        for sheet in response['sheets']:
            data = []
            for item in sheet['data']:
                for row in item.get('rowData', []):
                    row_data = []
                    for col in row.get('values', []):
                        effective_value = col.get('effectiveValue', None)
                        formatted = col.get('formattedValue', '')
                        if effective_value is None:
                            value = None
                            typ = GCellType.EMPTY
                        elif 'numberValue' in effective_value:
                            value = effective_value['numberValue']
                            t = col.get('effectiveFormat', {}).get('numberFormat', {}).get('type', 'NUMBER')
                            try:
                                typ = GCellType(t)
                            except ValueError:
                                typ = GCellType.UNKNOWN
                        elif 'stringValue' in effective_value:
                            value = effective_value['stringValue']
                            typ = GCellType.STRING
                        elif 'boolValue' in effective_value:
                            value = effective_value['boolValue']
                            typ = GCellType.BOOLEAN
                        elif 'errorValue' in effective_value:
                            msg = effective_value['errorValue']['message']
                            value = '{} ({})'.format(col['formattedValue'], msg)
                            typ = GCellType.ERROR
                        else:
                            value = formatted
                            typ = GCellType.UNKNOWN
                        row_data.append(GCell(value=value, type=typ, formatted=formatted))
                    data.append(row_data)
                cells[sheet['properties']['title']] = data
        return cells

    @staticmethod
    def to_datetime(value):
        """Convert a "serial number" date into a :class:`datetime.datetime`.

        Parameters
        ----------
        value : :class:`float`
            A date in the "serial number" format.

        Returns
        -------
        :class:`datetime.datetime`
            The date converted.
        """
        days = int(value)
        seconds = (value - days) * 86400  # 60 * 60 * 24
        return GSheets.SERIAL_NUMBER_ORIGIN + timedelta(days=days, seconds=seconds)

    def _get_range(self, sheet, cells, spreadsheet_id):
        if not sheet:
            names = self.sheet_names(spreadsheet_id)
            if len(names) != 1:
                sheets = ', '.join(repr(n) for n in names)
                raise ValueError('You must specify a sheet name: ' + sheets)
            _range = names[0]
        else:
            _range = sheet

        if cells:
            _range += '!{}'.format(cells)

        return _range

    @staticmethod
    def _values(values):
        """The append() and update() API methods require a list of lists."""
        if not isinstance(values, (list, tuple)):
            return [[values]]
        if values and not isinstance(values[0], (list, tuple)):
            return [values]
        return values


class GMail(GoogleAPI):

    def __init__(self, account=None, credentials=None, scopes=None):
        """Interact with Gmail.

        .. attention::
           You must follow the instructions in the prerequisites section for setting up the
           `Gmail API <https://developers.google.com/gmail/api/quickstart/python#prerequisites>`_
           before you can use this class. It is also useful to be aware of the
           `refresh token expiration <https://developers.google.com/identity/protocols/oauth2#expiration>`_
           policy.

        Parameters
        ----------
        account : :class:`str`, optional
            Since a person may have multiple Google accounts, and multiple people
            may run the same code, this parameter decides which token to load
            to authenticate with the Google API. The value can be any text (or
            :data:`None`) that you want to associate with a particular Google
            account, provided that it contains valid characters for a filename.
            The value that you chose when you authenticated with your `credentials`
            should be used for all future instances of this class to access that
            particular Google account. You can associate a different value with
            a Google account at any time (by passing in a different `account`
            value), but you will be asked to authenticate with your `credentials`
            again, or, alternatively, you can rename the token files located in
            :const:`~msl.io.constants.HOME_DIR` to match the new `account` value.
        credentials : :class:`str`, optional
            The path to the `client secrets` OAuth credential file. This
            parameter only needs to be specified the first time that you
            authenticate with a particular Google account or if you delete
            the token file that was created when you previously authenticated.
        scopes : :class:`list` of :class:`str`, optional
            The list of scopes to enable for the Google API. See
            `Gmail scopes <https://developers.google.com/identity/protocols/oauth2/scopes#gmail>`_
            for more details. If not specified then default scopes are chosen.
        """
        if not scopes:
            scopes = [
                'https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/gmail.metadata'
            ]

        super(GMail, self).__init__(
            'gmail', 'v1', credentials, scopes, False, account)

        self._my_email_address = None
        self._users = self._service.users()

    def profile(self):
        """Gets the authenticated user's Gmail profile.

        Returns
        -------
        :class:`dict`
            Returns the following

            .. code-block:: console

                {
                   'email_address': string, The authenticated user's email address
                   'messages_total': integer, The total number of messages in the mailbox
                   'threads_total': integer, The total number of threads in the mailbox
                   'history_id': string, The ID of the mailbox's current history record
                }

        """
        profile = self._users.getProfile(userId='me').execute()
        return {
            'email_address': profile['emailAddress'],
            'messages_total': profile['messagesTotal'],
            'threads_total': profile['threadsTotal'],
            'history_id': profile['historyId'],
        }

    def send(self, recipients, sender='me', subject=None, body=None):
        """Send an email.

        Parameters
        ----------
        recipients : :class:`str` or :class:`list` of :class:`str`
            The email address(es) of the recipient(s). The value ``'me'``
            can be used to indicate the authenticated user.
        sender : :class:`str`, optional
            The email address of the sender. The value ``'me'``
            can be used to indicate the authenticated user.
        subject : :class:`str`, optional
            The text to include in the subject field.
        body : :class:`str`, optional
            The text to include in the body of the email. The text can be
            enclosed in ``<html></html>`` tags to use HTML elements to format
            the message.

        See Also
        --------
        :func:`~msl.io.utils.send_email`
        """
        if isinstance(recipients, str):
            recipients = [recipients]

        for i in range(len(recipients)):
            if recipients[i] == 'me':
                if self._my_email_address is None:
                    self._my_email_address = self.profile()['email_address']
                recipients[i] = self._my_email_address

        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = subject or '(no subject)'

        text = body or ''
        subtype = 'html' if text.startswith('<html>') else 'plain'
        msg.attach(MIMEText(text, subtype))

        self._users.messages().send(
            userId=sender,
            body={'raw': b64encode(msg.as_bytes()).decode()}
        ).execute()
