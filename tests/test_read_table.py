from __future__ import unicode_literals
import os
import warnings
from datetime import datetime
from io import StringIO, BytesIO

import pytest
import numpy as np

from msl.io import read_table
from msl.io.tables import _google_file_id_regex

from test_google_api import (
    skipif_no_gsheets_personal,
    skipif_no_gdrive_personal,
)

# the data in the Excel, CVS and TXT files that are tested contain the following
header = np.asarray(['timestamp', 'val1', 'uncert1', 'val2', 'uncert2'], dtype=str)
data = np.asarray([
    ('2019-09-11 14:06:55', -0.505382, 0.000077, 0.501073, 0.000079),
    ('2019-09-11 14:06:59', -0.505191, 0.000066, 0.500877, 0.000083),
    ('2019-09-11 14:07:03', -0.505308, 0.000086, 0.500988, 0.000087),
    ('2019-09-11 14:07:07', -0.505250, 0.000119, 0.500923, 0.000120),
    ('2019-09-11 14:07:11', -0.505275, 0.000070, 0.500965, 0.000088),
    ('2019-09-11 14:07:15', -0.505137, 0.000079, 0.500817, 0.000085),
    ('2019-09-11 14:07:19', -0.505073, 0.000099, 0.500786, 0.000084),
    ('2019-09-11 14:07:23', -0.505133, 0.000088, 0.500805, 0.000076),
    ('2019-09-11 14:07:27', -0.505096, 0.000062, 0.500759, 0.000062),
    ('2019-09-11 14:07:31', -0.505072, 0.000142, 0.500739, 0.000149),
], dtype='U19,f8,f8,f8,f8')

# the data in the GSheet spreadsheet
gsheet_header = np.asarray(['Timestamp', 'Value', 'Valid', 'ID'])
gsheet_data = np.asarray([
    (datetime(2019, 9, 11, 14, 6, 55), 20.1, True, 'sensor 1'),
    (datetime(2019, 9, 11, 14, 6, 59), 25.4, False, 'sensor 2'),
    (datetime(2019, 9, 11, 14, 7, 3), 19.4, True, 'sensor 3'),
    (datetime(2019, 9, 11, 14, 7, 7), 11.8, False, 'sensor 4'),
    (datetime(2019, 9, 11, 14, 7, 11), 24.6, False, 'sensor 5'),
    (datetime(2019, 9, 11, 14, 7, 15), 20.7, True, 'sensor 1'),
    (datetime(2019, 9, 11, 14, 7, 19), 21.8, True, 'sensor 2'),
    (datetime(2019, 9, 11, 14, 7, 23), 19.2, True, 'sensor 3'),
    (datetime(2019, 9, 11, 14, 7, 27), 18.6, False, 'sensor 4'),
    (datetime(2019, 9, 11, 14, 7, 31), 16.4, False, 'sensor 5'),
])


def get_url(extension):
    return os.path.join(os.path.dirname(__file__), 'samples', 'table' + extension)


def test_raises():

    # file does not exist
    with pytest.raises(IOError):
        read_table('does not exist')

    # the unpack argument is not supported for text-based files
    with pytest.raises(ValueError, match='unpack'):
        read_table(get_url('.csv'), unpack=True)

    # invalid range of cells for Excel
    for c in ['A-B', 'A:B', ':', '', 'A2', 'A2:', 'A2:B']:
        with pytest.raises(ValueError, match=r'You must specify a valid cell range'):
            read_table(get_url('.xls'), cell=c)


def test_fetch_all_data():
    params = [
        ('.csv', dict(dtype=data.dtype)),
        ('.txt', dict(dtype=data.dtype, delimiter='\t')),
        ('.xls', dict(dtype=data.dtype, sheet='A1', as_datetime=False)),
        ('.xls', dict(dtype=data.dtype, sheet='BH11', as_datetime=False, cell='BH11:BL21')),
        ('.xls', dict(dtype=data.dtype, sheet='BH11', as_datetime=False, cell='$BH$11:$BL$21')),
        ('.xls', dict(dtype=data.dtype, sheet='BH11', as_datetime=False, cell='bh11:bl21')),
        ('.xlsx', dict(dtype=data.dtype, sheet='A1', as_datetime=False)),
        ('.xlsx', dict(dtype=data.dtype, sheet='BH11', as_datetime=False, cell='BH11:BL21')),
        ('.xlsx', dict(dtype=data.dtype, sheet='AEX154041', as_datetime=False, cell='AEX154041:AFB154051')),
    ]
    for extn, kwargs in params:
        dset = read_table(get_url(extn), **kwargs)
        assert np.array_equal(dset.metadata.header, header)
        assert np.array_equal(dset.data, data)
        assert dset.shape == (10,)


def test_ignore_timestamp_column():
    floats = np.asarray([[e['f1'], e['f2'], e['f3'], e['f4']] for e in data])
    params = [
        ('.csv', dict(usecols=(1, 2, 3, 4))),
        ('.txt', dict(usecols=(1, 2, 3, 4), delimiter='\t')),
        ('.xls', dict(sheet='A1', cell='B1:E11')),
        ('.xls', dict(sheet='BH11', cell='BI11:BL21')),
        ('.xlsx', dict(sheet='A1', cell='B1:E11')),
        ('.xlsx', dict(sheet='BH11', cell='BI11:BL21')),
        ('.xlsx', dict(sheet='AEX154041', cell='AEY154041:AFB154051')),
    ]
    for extn, kwargs in params:
        dset = read_table(get_url(extn), **kwargs)
        assert np.array_equal(dset.metadata.header, header[1:])
        assert np.array_equal(dset.data, floats)
        assert dset.shape == (10, 4)


def test_single_column():
    params = [
        ('.csv', dict(usecols=1)),
        ('.txt', dict(usecols=1, delimiter='\t')),
        ('.xls', dict(sheet='A1', cell='B1:B11')),
        ('.xls', dict(sheet='BH11', cell='BI11:BI21')),
        ('.xlsx', dict(sheet='A1', cell='B1:B11')),
        ('.xlsx', dict(sheet='BH11', cell='BI11:BI21')),
        ('.xlsx', dict(sheet='AEX154041', cell='AEY154041:AEY154051')),
    ]
    for extn, kwargs in params:
        dset = read_table(get_url(extn), **kwargs)
        assert np.array_equal(dset.metadata.header, [header[1]])
        assert np.array_equal(dset.data, data['f1'])
        assert dset.shape == (10,)


def test_single_row():
    params = [
        ('.csv', dict(dtype=data.dtype, max_rows=1)),
        ('.txt', dict(dtype=data.dtype, max_rows=1, delimiter='\t')),
        ('.xls', dict(dtype=data.dtype, sheet='A1', as_datetime=False, cell='A1:E2')),
        ('.xls', dict(dtype=data.dtype, sheet='BH11', as_datetime=False, cell='BH11:BL12')),
        ('.xlsx', dict(dtype=data.dtype, sheet='A1', as_datetime=False, cell='A1:E2')),
        ('.xlsx', dict(dtype=data.dtype, sheet='BH11', as_datetime=False, cell='BH11:BL12')),
        ('.xlsx', dict(dtype=data.dtype, sheet='AEX154041', as_datetime=False, cell='AEX154041:AFB154042')),
    ]
    for extn, kwargs in params:
        dset = read_table(get_url(extn), **kwargs)
        assert np.array_equal(dset.metadata.header, header)
        assert np.array_equal(dset.data, data[0])


def test_header_only():
    params = [
        ('.csv', dict(dtype=str, max_rows=0)),
        ('.txt', dict(dtype=str, max_rows=0, delimiter='\t')),
        ('.xls', dict(sheet='A1', as_datetime=False, cell='A1:E1')),
        ('.xls', dict(sheet='BH11', as_datetime=False, cell='BH11:BL11')),
        ('.xlsx', dict(sheet='A1', as_datetime=False, cell='A1:E1')),
        ('.xlsx', dict(sheet='BH11', as_datetime=False, cell='BH11:BL11')),
        ('.xlsx', dict(sheet='AEX154041', as_datetime=False, cell='AEX154041:AFB154041')),
    ]
    for extn, kwargs in params:
        dset = read_table(get_url(extn), **kwargs)
        assert np.array_equal(dset.metadata.header, header)
        assert dset.data.size == 0


def test_datetime_objects():
    def to_datetime(string):
        return datetime.strptime(string.decode(), '%Y-%m-%d %H:%M:%S')

    dt = {'names': header, 'formats': [object, float, float, float, float]}
    datetimes = np.asarray([to_datetime(item.encode()) for item in data['f0']], dtype=object)
    data_datetimes = np.asarray([
        (a, b, c, d, e) for a, b, c, d, e in zip(datetimes, data['f1'], data['f2'], data['f3'], data['f4'])
    ], dtype=dt)

    params = [
        ('.csv', dict(dtype=dt, converters={0: to_datetime})),
        ('.txt', dict(dtype=dt, converters={0: to_datetime}, delimiter='\t')),
        ('.xls', dict(dtype=dt, sheet='A1')),
        ('.xls', dict(dtype=dt, sheet='BH11', cell='BH11:BL21')),
        ('.xlsx', dict(dtype=dt, sheet='A1')),
        ('.xlsx', dict(dtype=dt, sheet='BH11', cell='BH11:BL21')),
        ('.xlsx', dict(dtype=dt, sheet='AEX154041', cell='AEX154041:AFB154051')),
    ]
    for extn, kwargs in params:
        dset = read_table(get_url(extn), **kwargs)
        assert np.array_equal(dset.metadata.header, header)
        for h in header:
            assert np.array_equal(dset[h], data_datetimes[h])
        assert dset.shape == (10,)


def test_skip_rows():
    params = [
        ('.csv', dict(dtype=data.dtype, skiprows=5)),
        ('.txt', dict(dtype=data.dtype, delimiter='\t', skiprows=5)),
    ]
    new_header = ['2019-09-11 14:07:07', '-0.505250', '0.000119', '0.500923', '0.000120']
    for extn, kwargs in params:
        dset = read_table(get_url(extn), **kwargs)
        assert np.array_equal(dset.metadata.header, new_header)
        assert np.array_equal(dset.data, data[4:])
        assert dset.shape == (6,)

    params = [
        ('.csv', dict(skiprows=100)),
        ('.txt', dict(skiprows=100)),
    ]
    for extn, kwargs in params:
        dset = read_table(get_url(extn), **kwargs)
        assert dset.metadata.header.size == 0
        assert dset.size == 0


def test_text_file_like():
    params = [
        ('.csv', dict(dtype=data.dtype, delimiter=',')),
        ('.txt', dict(dtype=data.dtype, delimiter='\t')),
    ]

    def assert_dataset(dataset):
        assert np.array_equal(dataset.metadata.header, header)
        assert np.array_equal(dataset.data, data)
        assert dataset.shape == (10,)

    for extn, kwargs in params:
        # first, load it using the file path to get it into a Dataset object
        dset_temp = read_table(get_url(extn), **kwargs)

        with StringIO() as buf:
            delim = kwargs['delimiter']
            buf.write(delim.join(h for h in dset_temp.metadata.header) + '\n')
            for row in dset_temp:
                buf.write(delim.join(str(val) for val in row) + '\n')

            buf.seek(0)
            dset = read_table(buf, **kwargs)
            assert dset.name == 'StringIO'
            assert_dataset(dset)

        with open(get_url(extn), 'r') as fp:
            dset = read_table(fp, **kwargs)
            assert dset.name == 'table' + extn
            assert_dataset(dset)

        kwargs['delimiter'] = kwargs['delimiter'].encode()

        with BytesIO() as buf:
            delim = kwargs['delimiter']
            buf.write(delim.join(h.encode() for h in dset_temp.metadata.header) + b'\n')
            for row in dset_temp:
                buf.write(delim.join(str(val).encode() for val in row) + b'\n')

            buf.seek(0)
            dset = read_table(buf, **kwargs)
            assert dset.name == 'BytesIO'
            assert_dataset(dset)

        with open(get_url(extn), 'rb') as fp:
            dset = read_table(fp, **kwargs)
            assert dset.name == 'table' + extn
            assert_dataset(dset)


def test_excel_file_pointer():
    params = [
        ('.xls', dict(dtype=data.dtype, sheet='A1', as_datetime=False)),
        ('.xlsx', dict(dtype=data.dtype, sheet='A1', as_datetime=False)),
    ]

    for extn, kwargs in params:
        for mode in ['rt', 'rb']:
            with open(get_url(extn), mode=mode) as fp:
                dataset = read_table(fp, **kwargs)
                assert np.array_equal(dataset.metadata.header, header)
                assert np.array_equal(dataset.data, data)
                assert dataset.shape == (10,)

    # there is no point to test StringIO nor BytesIO because `read_table`
    # checks the file path extension to decide how to read the table
    # and a StringIO and a BytesIO object do not have an extension to check
    # so read_table_excel will not be called, also xlrd cannot load a file stream


def test_google_file_id_regex():
    assert _google_file_id_regex.search('1Q0TAgnw6AJQWkLMf8V3qEhEXuCEXTFAc95cEcshOXnQ')
    assert _google_file_id_regex.search('1IemLij3ggB_S5ASO7qyPSIQUmvhWgBfemePn7gu_Je4')

    # does not start with 1
    assert not _google_file_id_regex.search('IemLij3ggB_S5ASO7qyPSIQUmvhWgBfemePn7gu_Je41')

    # not 44 characters
    for n in [0, 10, 40, 42, 43, 45, 50, 100]:
        assert not _google_file_id_regex.search('1' * n)

    # contains a "space", "/", "\", ":"
    assert not _google_file_id_regex.search('1IemLij3ggB S5ASO7qyPSIQUmvhWgBfemePn7gu_Je4')
    assert not _google_file_id_regex.search('1IemLij3ggB/S5ASO7qyPSIQUmvhWgBfemePn7gu_Je4')
    assert not _google_file_id_regex.search('1IemLij3ggB:S5ASO7qyPSIQUmvhWgBfemePn7gu_Je4')
    assert not _google_file_id_regex.search(r'1IemLij3ggB\S5ASO7qyPSIQUmvhWgBfemePn7gu_Je4')


@skipif_no_gsheets_personal
def test_gsheets():
    # ID of the table.gsheet file
    table_id = '1Q0TAgnw6AJQWkLMf8V3qEhEXuCEXTFAc95cEcshOXnQ.gsheet'

    dset = read_table(table_id, is_corporate_account=False, sheet='A1')
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, gsheet_data)

    dset = read_table(table_id, is_corporate_account=False, sheet='A1', cell='A1')
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, gsheet_data)

    dset = read_table(table_id, is_corporate_account=False, sheet='A1', cell='A2')
    assert np.array_equal(dset.metadata.header, [str(item) for item in gsheet_data[0]])
    assert np.array_equal(dset, gsheet_data[1:])

    dset = read_table(table_id, is_corporate_account=False, sheet='A1', cell='A4:C7')
    assert np.array_equal(dset.metadata.header, ['2019-09-11 14:07:03', '19.4', 'True'])
    assert np.array_equal(dset, gsheet_data[3:6, :3])

    dset = read_table(table_id, is_corporate_account=False, sheet='A1', as_datetime=False)
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset.data, gsheet_data.astype(str))

    dset = read_table(table_id, is_corporate_account=False, sheet='A1', as_datetime=False, dtype=object)
    data2 = gsheet_data.copy()
    data2[:, 0] = [str(item) for item in gsheet_data[:, 0]]
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, data2)

    dset = read_table(table_id, is_corporate_account=False, sheet='A1', cell='B1:B11')
    assert np.array_equal(dset.metadata.header, [gsheet_header[1]])
    assert np.array_equal(dset, gsheet_data[:, 1])

    dset = read_table(table_id, is_corporate_account=False, sheet='A1', cell='A$1:D$2')
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, gsheet_data[0])

    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=np.VisibleDeprecationWarning)
        dset = read_table(table_id, is_corporate_account=False, sheet='H22')
        assert dset.metadata.header.size == 0
        assert dset.shape == (31,)
        for i in range(20):
            assert dset[i] == ()
        assert np.array_equal(dset[20][:7], [None] * 7)
        assert np.array_equal(dset[20][7:], gsheet_header)
        for i, row in enumerate(gsheet_data, start=21):
            assert np.array_equal(dset[i][:7], [None] * 7)
            assert np.array_equal(dset[i][7:], row)

    dset = read_table(table_id, is_corporate_account=False, sheet='H22', cell='H22')
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, gsheet_data)

    dset = read_table(table_id, is_corporate_account=False, sheet='H22', cell='$h$22:$k$32')
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, gsheet_data)

    dset = read_table(table_id, is_corporate_account=False, sheet='header only')
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert dset.size == 0

    dset = read_table(table_id, is_corporate_account=False, sheet='empty')
    assert dset.metadata.header.size == 0
    assert dset.size == 0

    dset = read_table(table_id, is_corporate_account=False, sheet='column')
    assert np.array_equal(dset.metadata.header, [gsheet_header[1]])
    assert np.array_equal(dset, gsheet_data[:, 1])

    dset = read_table(table_id, is_corporate_account=False, sheet='row')
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, gsheet_data[0])

    # ID of MSL/msl-io-testing/Copy of table.gsheet
    dset = read_table('1NfDUZzHk71CPAfhIoE8l9h4NJ8oeqKfqGAUM81Vyc88.gsheet', is_corporate_account=False, sheet='A1')
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, gsheet_data)


@skipif_no_gdrive_personal
@skipif_no_gsheets_personal
def test_gsheet_file_path():
    dset = read_table('table.gsheet', is_corporate_account=False, sheet='A1')
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, gsheet_data)

    dset = read_table('MSL/msl-io-testing/Copy of table.gsheet', is_corporate_account=False, sheet='A1')
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, gsheet_data)

    # this is a way to pass in a pointer to a Google Sheets file
    # that does not exist on the computer running the tests
    filename = 'table.gsheet'
    with open(filename, mode='w'):
        pass
    with open(filename, mode='r') as fp:
        dset = read_table(fp, is_corporate_account=False, sheet='A1')
    assert np.array_equal(dset.metadata.header, gsheet_header)
    assert np.array_equal(dset, gsheet_data)
    os.remove(filename)
