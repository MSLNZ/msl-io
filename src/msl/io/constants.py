"""Constants used by `msl-io`."""

from __future__ import annotations

import os
from pathlib import Path

# If this module is run via "sudo python" on a Raspberry Pi the value of
# os.path.expanduser('~') becomes '/root' instead of '/home/pi'. On Linux using
# "sudo python" keeps os.path.expanduser('~') as /home/<username> and running this
# module in an elevated command prompt on Windows keeps os.path.expanduser('~')
# as C:\\Users\\<username>. Therefore defining USER_DIR in the following way keeps
# things more consistent across more platforms.
USER_DIR = Path("~" + os.getenv("SUDO_USER", "")).expanduser()

MSL_IO_DIR = Path(os.getenv("MSL_IO_DIR", USER_DIR / ".msl" / "io"))
"""[pathlib.Path][] &mdash; The default directory where all files that are used by `msl-io` are located.

Can be overwritten by specifying an `MSL_IO_DIR` environment variable.
"""
