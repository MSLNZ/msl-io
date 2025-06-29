"""Reader for the [HDF5] file format.

!!! attention
    This Reader loads the entire [HDF5] file in memory. If you need to use any
    of the more advanced features of an [HDF5] file, it is best to directly load
    the file using [h5py](https://www.h5py.org/).

[HDF5]: https://www.hdfgroup.org/
"""

from __future__ import annotations

import os
from io import BufferedIOBase
from typing import TYPE_CHECKING, no_type_check

try:
    import h5py  # type: ignore[import-untyped]  # pyright: ignore[reportMissingTypeStubs]
except ImportError:
    h5py = None

from msl.io.base import Reader, register

if TYPE_CHECKING:
    from typing import IO, Any


@register
class HDF5Reader(Reader):
    """Reader for the [HDF5](https://www.hdfgroup.org/) file format."""

    @staticmethod
    def can_read(file: IO[str] | IO[bytes] | str, **kwargs: Any) -> bool:  # noqa: ARG004
        r"""The [HDF5] file format has a standard [signature].

        The first 8 bytes must be `\\x89HDF\\r\\n\\x1a\\n`.

        [HDF5]: https://www.hdfgroup.org/
        [signature]: https://support.hdfgroup.org/HDF5/doc/H5.format.html#Superblock

        Args:
            file: The file to check.
            kwargs: All keyword arguments are ignored.
        """
        if isinstance(file, (str, BufferedIOBase)):
            return Reader.get_bytes(file, 8) == b"\x89HDF\r\n\x1a\n"
        return False

    def read(self, **kwargs: Any) -> None:
        """Reads the [HDF5](https://www.hdfgroup.org/) file.

        Args:
            kwargs: All keyword arguments are passed to [h5py.File][].
        """
        if h5py is None:
            msg = "You must install h5py to read HDF5 files, run\n  pip install h5py"
            raise ImportError(msg)

        @no_type_check
        def convert(name: str, obj: object) -> None:
            head, tail = os.path.split(name)
            s = self["/" + head] if head else self
            if isinstance(obj, h5py.Dataset):
                _ = s.create_dataset(tail, data=obj[:], **obj.attrs)
            elif isinstance(obj, h5py.Group):
                _ = s.create_group(tail, **obj.attrs)
            else:
                msg = f"Should never get here, unhandled h5py object {obj}"
                raise TypeError(msg)

        @no_type_check
        def h5_open(f: BufferedIOBase) -> None:
            with h5py.File(f, mode="r", **kwargs) as h5:
                self.add_metadata(**h5.attrs)
                h5.visititems(convert)  # cSpell: ignore visititems

        # Calling h5py.File on a file on a mapped drive could raise
        # an OSError. This occurred when a local folder was shared
        # and then mapped on the same computer. Opening the file
        # using open() and then passing in the file handle to
        # h5py.File is more universal
        if isinstance(self.file, BufferedIOBase):
            h5_open(self.file)
        elif isinstance(self.file, str):
            with open(self.file, mode="rb") as fp:  # noqa: PTH123
                h5_open(fp)
        else:
            msg = f"Should never get here, file type is {type(self.file)}"
            raise TypeError(msg)
