import os
from datetime import datetime

import pytest
import numpy as np

from msl.io import read_table

# the data in the files that are tested contain the following
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


def get_url(extension):
    return os.path.join(os.path.dirname(__file__), 'samples', 'table' + extension)


def test_raises():

    # url does not exist
    with pytest.raises(IOError):
        read_table('does not exist')

    # the unpack argument is not supported for text-based files
    with pytest.raises(ValueError) as e:
        read_table(get_url('.csv'), unpack=True)
    assert 'unpack' in str(e.value)

    # invalid range of cells
    for c in ['A-B', 'A:B', ':', '', 'A2', 'A2:', 'A2:B']:
        with pytest.raises(ValueError) as e:
            read_table(get_url('.xls'), cell=c)
        assert 'You must specify a range of cells' in str(e.value)


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
        ('.csv', dict(dtype=data.dtype, max_rows=1)),  # skiprows is 1 by default
        ('.txt', dict(dtype=data.dtype, max_rows=1, delimiter='\t')),  # skiprows is 1 by default
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
        ('.csv', dict(dtype=str, skiprows=0, max_rows=1)),
        ('.txt', dict(dtype=str, skiprows=0, max_rows=1, delimiter='\t')),
        ('.xls', dict(sheet='A1', as_datetime=False, cell='A1:E1')),
        ('.xls', dict(sheet='BH11', as_datetime=False, cell='BH11:BL11')),
        ('.xlsx', dict(sheet='A1', as_datetime=False, cell='A1:E1')),
        ('.xlsx', dict(sheet='BH11', as_datetime=False, cell='BH11:BL11')),
        ('.xlsx', dict(sheet='AEX154041', as_datetime=False, cell='AEX154041:AFB154041')),
    ]
    for extn, kwargs in params:
        dset = read_table(get_url(extn), **kwargs)
        assert np.array_equal(dset.metadata.header, header)
        assert np.array_equal(dset.data, header)
        assert dset.shape == (5,)


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
