from pathlib import Path
from datetime import datetime

from msl.io import Dataset, read
from msl.io.readers import RegularTransmittanceReader


def test_spectrophotometer_trans() -> None:
    root = read(Path(__file__).parent / "samples" / "Trans_002420.dat")
    assert isinstance(root, RegularTransmittanceReader)

    assert "trans_data" in root
    assert "data" in root["trans_data"]

    assert root['trans_data']['data'].metadata['start_time'] == datetime(2024, 4, 2, 13, 31, 39)
    assert root['trans_data']['data'].metadata['avg_temp'] == 23.09999999999999
    assert root['trans_data']['data'].metadata['wavelength input'] == 'Read from text file'
    assert root['trans_data']['data'].metadata['delay'] == 3.0

    assert root['trans_data']['data'].metadata['comment'].startswith("0.625 mm slits")

    dat = root['trans_data']['data']
    wavelength = dat['wavelength']
    assert len(wavelength) == 195
    assert wavelength[0] == 398.784
    assert wavelength[30] == 898.996
    assert wavelength[194] == 1001.0

    signal = dat['signal']
    assert len(signal) == 195
    assert signal[5] == 0.805702388
    assert signal[62] == 0.720496178

    u_signal = dat['u_signal']
    assert len(u_signal) == 195
    assert u_signal[35] == 0.000170391
    assert u_signal[104] == 7.5779e-05

    mon_signal = dat['mon_signal']
    assert len(mon_signal) == 195
    assert mon_signal[13] == 0.39653053
    assert mon_signal[59] == 0.291961366

    u_mon_signal = dat['u_mon_signal']
    assert len(u_mon_signal) == 195
    assert u_mon_signal[24] == 2.4791e-05
    assert u_mon_signal[124] == 6.7492e-05

    correlation = dat["correlation"]
    assert len(correlation) == 195
    assert correlation[91] == 0.704452873
    assert correlation[151] == 0.589505627

    dark_current = dat["dark_current"]
    assert len(dark_current) == 195
    assert dark_current[64] == -0.000166063
    assert dark_current[133] == -0.000158816

    u_dark_current = dat["u_dark_current"]
    assert len(u_dark_current) == 195
    assert u_dark_current[111] == 2.74e-06
    assert u_dark_current[147] == 2.656e-06

    mon_dark = dat["mon_dark"]
    assert len(mon_dark) == 195
    assert mon_dark[65] == 5.2626e-05
    assert mon_dark[150] == 5.3167e-05

    u_mon_dark = dat["u_mon_dark"]
    assert len(u_mon_dark) == 195
    assert u_mon_dark[88] == 1.236e-06
    assert u_mon_dark[191] == 1.127e-06
