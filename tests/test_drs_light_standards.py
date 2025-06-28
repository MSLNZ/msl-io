from msl.io.node import Dataset
from msl.io.readers import DRSReader
from tests.helper import read_sample


def test_drs() -> None:
    root = read_sample("Lamp_15082018_4.DAT")
    assert isinstance(root, DRSReader)

    assert "run1" in root
    assert "scan1" in root["run1"]
    assert "run2" in root
    assert "scan1" in root["run2"]
    assert "run3" in root
    assert "scan1" in root["run3"]
    assert "run4" in root
    assert "scan1" in root["run4"]

    assert root["run1"].metadata["wavelength_start"] == 600
    assert root["run2"].metadata["wavelength_start"] == 700
    assert root["run3"].metadata["wavelength_increment"] == 50
    assert root["run4"].metadata["wavelength_end"] == 1000

    assert root.run1.metadata.comment.startswith("Comparison F 637 vs F636")

    assert root.run2.metadata.devices["LAMP 1"]["Name"] == "F636"
    assert root.run2.metadata.devices["LAMP 2"]["Name"] == "F637"
    assert root.run3.metadata.devices["LAMP 1"]["Name"] == "F637"
    assert root.run3.metadata.devices["LAMP 2"]["Name"] == "F636"

    dat = root["run1"]["scan1"]["dat"]
    log636 = root["run1"]["scan1"]["log-F636"]
    log637 = root["run1"]["scan1"]["log-F637"]
    assert root.is_dataset(dat)
    assert isinstance(dat, Dataset)
    assert root.is_dataset(log636)
    assert isinstance(log636, Dataset)
    assert root.is_dataset(log637)
    assert dat["F636"][1] == 2.98123609
    assert dat["u(F636)"][1] == 0.00066831
    assert abs(log636.wavelength[0] - 600) < 0.001

    dat = root["run3"]["scan1"]["dat"]
    log636 = root["run3"]["scan1"]["log-F636"]
    log637 = root["run3"]["scan1"]["log-F637"]
    assert root.is_dataset(dat)
    assert isinstance(dat, Dataset)
    assert root.is_dataset(log636)
    assert isinstance(log636, Dataset)
    assert root.is_dataset(log637)
    assert dat["F636"][3] == 0.90075543
    assert dat["u(F636)"][3] == 0.00032893
    assert abs(log636.wavelength[4] - 800) < 0.001
