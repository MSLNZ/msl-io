from __future__ import annotations

import os
import re
from datetime import datetime
from typing import TYPE_CHECKING

import numpy as np

from msl.io import Reader
from msl.io.utils import get_extension

if TYPE_CHECKING:
    from typing import Any

    from msl.io.types import ReadLike


class RegularTransmittanceReader(Reader):
    """Reader for Trans files from Light Standards at MSL."""

    @staticmethod
    def can_read(file: ReadLike | str, **kwargs: Any) -> bool:  # noqa: ARG004
        """Checks is the file extension is .dat and the filename starts with 'Trans'.

        Args:
            file: file to be read
            kwargs: All keyword arguments are ignored.
        """
        if get_extension(file).lower() != ".dat":
            return False
        return "Trans_" in Path.name(file)

    def read(self, **kwargs: Any) -> None:
        """Reads the data in the corresponding log file.

        Args:
            kwargs: All keyword arguments are ignored.
        """
        assert isinstance(self.file, str)  # noqa: S101
        lines_log = self.get_lines(self.file[:-3] + "log", remove_empty_lines=True)
        num_lines_log = len(lines_log)
        group = self.create_group("trans_data")
        meta: dict[str, Any] = {}

        meta["start_time"] = self._convert_time(lines_log[0].split(",")[1], lines_log[1])
        try:
            meta["end_time"] = self._convert_time(lines_log[-2].split(",")[1], lines_log[-1])
        except IndexError:
            meta["note"] = "No end time recorded."
        this_line = 2

        # Read temperature data out of celsius file
        meta["avg_temp"] = self._read_celsius_file()

        # skip lines until we get to the wavelength information and save comment
        comment = []
        while not lines_log[this_line].startswith("Wavelengths Settings:"):
            comment.append(lines_log[this_line])
            this_line += 1

        meta["comment"] = "\n".join(comment)
        this_line += 1

        if lines_log[this_line].startswith("Wavelengths read"):
            meta["wavelength input"] = "Read from text file"
        else:
            meta["wavelength input"] = "Manually input"

        while not lines_log[this_line].startswith("TEST MODULE:"):
            this_line += 1

        this_line += 1
        if lines_log[this_line].startswith("DVM INIT"):
            meta["dvm init"] = lines_log[this_line]

        this_line += 2
        if lines_log[this_line].startswith("DELAY"):
            meta["delay"] = float(lines_log[this_line].split()[1])

        this_line += 2
        if lines_log[this_line].startswith("NUM SAMPLES"):
            n_samples = int(lines_log[this_line].split()[2])
            meta["n_samples"] = n_samples

        wavelengths = []
        dark_current = []
        dark_current_u = []
        dark_current_m = []
        dark_current_m_u = []
        i0 = []
        i0_u = []
        m0 = []
        m0_u = []
        corr = []
        is_ = []
        is_u = []
        is_m = []
        is_m_u = []
        is_corr = []

        n_measurements = 0

        while this_line < num_lines_log - 1:
            if lines_log[this_line].startswith("Wavelength = "):
                n_measurements += 1
                wavelengths.append(lines_log[this_line].split()[2])
                i0.append(float(re.split("=|\t", lines_log[this_line + 1])[1]))
                i0_u.append(float(re.split("=|\t", lines_log[this_line + 1])[3]))
                m0.append(float(re.split("=|\t", lines_log[this_line + 2])[1]))
                m0_u.append(float(re.split("=|\t", lines_log[this_line + 2])[3]))
                corr.append(float(lines_log[this_line + 3].split("=")[1]))
                dark_current.append(float(re.split("=|\t", lines_log[this_line + 4])[1]))
                dark_current_u.append(float(re.split("=|\t", lines_log[this_line + 4])[3]))
                dark_current_m.append(float(re.split("=|\t", lines_log[this_line + 5])[1]))
                dark_current_m_u.append(float(re.split("=|\t", lines_log[this_line + 5])[3]))
                is_.append(tuple([float(item) for item in lines_log[this_line + 7].split("|")[1:] if item]))
                is_u.append(tuple([float(item) for item in lines_log[this_line + 8].split("|")[1:] if item]))
                is_m.append(tuple([float(item) for item in lines_log[this_line + 9].split("|")[1:] if item]))
                is_m_u.append(tuple([float(item) for item in lines_log[this_line + 10].split("|")[1:] if item]))
                is_corr.append(tuple([float(item) for item in lines_log[this_line + 11].split("|")[1:] if item]))

                this_line += 10

            else:
                this_line += 1

        fieldnames = [
            "wavelength",
            "signal",
            "u_signal",
            "mon_signal",
            "u_mon_signal",
            "correlation",
            "dark_current",
            "u_dark_current",
            "mon_dark",
            "u_mon_dark",
        ]
        data = np.array(
            list(
                zip(
                    wavelengths,
                    i0,
                    i0_u,
                    m0,
                    m0_u,
                    corr,
                    dark_current,
                    dark_current_u,
                    dark_current_m,
                    dark_current_m_u,
                )
            ),
            dtype=[(name, float) for name in fieldnames],
        )
        group.create_dataset("data", data=data, dtype=[(name, float) for name in fieldnames], **meta)

        fieldnames = [
            "Transmitted signal",
            "u(Transmitted signal)",
            "Monitor transmitted",
            "u(Monitor transmitted)",
            "Transmitted correlation",
        ]
        dnames = ["Is", "Is_u", "Is_M", "Is_M_u", "Is_corr"]
        sample_data = np.array(
            (list(zip(*is_)), list(zip(*is_u)), list(zip(*is_m)), list(zip(*is_m_u)), list(zip(*is_corr)))
        )
        ind = 1
        for sample in sample_data:
            group.create_dataset(
                dnames[ind - 1], data=np.array(sample), dtype=[(name, float) for name in fieldnames], **meta
            )
            ind += 1

    def _convert_date(self, date_str: str) -> datetime:
        """Converts string of date into datestring object.

        :param date_str: string containing date in date month year format with month written in full
        :return: datetime object corresponding to the date
        """
        return datetime.strptime(date_str, "%d %B %Y")

    def _convert_time(self, date_str: str, time_str: str) -> datetime:
        """Converts string of date and time into datestring object.

        :param date_str: string containing date in date month year format with month written in full
        :param time_str: string containing time in hours:minutes:seconds am/pm format
        :return: datetime object corresponding to the time and date
        """
        return datetime.strptime(date_str + " " + time_str, " %d %B %Y %I:%M:%S %p")

    def _read_celsius_file(self) -> Any:
        assert isinstance(self.file, str)  # noqa: S101
        lines_celsius = self.get_lines(self.file[:-3] + "celsius", remove_empty_lines=True)
        num_lines = len(lines_celsius)
        t1 = []
        t2 = []
        t3 = []
        this_line = 0
        while this_line < num_lines - 1:
            temp_data = lines_celsius[this_line].split()
            t1.append(float(temp_data[0]))
            t2.append(float(temp_data[1]))
            t3.append(float(temp_data[2]))
            this_line += 1
        temperatures = np.array([np.array(t2), np.array(t3)])
        return np.mean(temperatures)
