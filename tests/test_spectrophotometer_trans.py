from pathlib import Path

from msl.io import Dataset, read
from msl.io.readers import RegularTransmittanceReader


def test_spectrophotometer_trans() -> None:
    root = read(Path(__file__).parent / "samples" / "Trans_002420.dat")
    assert isinstance(root, RegularTransmittanceReader)

    assert "trans_data" in root
    assert "data" in root["trans_data"]

    dat = root["trans_data"]["data"]
    assert isinstance(dat, Dataset)
    assert len(dat["wavelength"]) == 195
    assert dat["wavelength"][0] == 398.784
    assert dat["wavelength"][30] == 898.996
    assert dat["wavelength"][194] == 1001.0

    assert len(dat["signal"]) == 195
    assert dat["signal"][5] == 0.805702388
    assert dat["signal"][62] == 0.720496178

    assert len(dat["u_signal"]) == 195
    assert dat["u_signal"][35] == 0.000170391
    assert dat["u_signal"][104] == 7.5779e-05

    assert len(dat["mon_signal"]) == 195
    assert dat["mon_signal"][13] == 0.39653053
    assert dat["mon_signal"][59] == 0.291961366

    assert len(dat["u_mon_signal"]) == 195
    assert dat["u_mon_signal"][24] == 2.4791e-05
    assert dat["u_mon_signal"][124] == 6.7492e-05

    assert len(dat["correlation"]) == 195
    assert dat["correlation"][91] == 0.704452873
    assert dat["correlation"][151] == 0.589505627

    assert len(dat["dark_current"]) == 195
    assert dat["dark_current"][64] == -0.000166063
    assert dat["dark_current"][133] == -0.000158816

    assert len(dat["u_dark_current"]) == 195
    assert dat["u_dark_current"][111] == 2.74e-06
    assert dat["u_dark_current"][147] == 2.656e-06

    assert len(dat["mon_dark"]) == 195
    assert dat["mon_dark"][65] == 5.2626e-05
    assert dat["mon_dark"][150] == 5.3167e-05

    assert len(dat["u_mon_dark"]) == 195
    assert dat["u_mon_dark"][88] == 1.236e-06
    assert dat["u_mon_dark"][191] == 1.127e-06
