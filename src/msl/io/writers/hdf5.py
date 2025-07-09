from __future__ import annotations

import os
from typing import TYPE_CHECKING, no_type_check

import numpy as np

try:
    import h5py  # type: ignore[import-untyped]  # pyright: ignore[reportMissingTypeStubs]
except ImportError:
    h5py = None

from msl.io.base import Writer
from msl.io.metadata import Metadata
from msl.io.node import Group
from msl.io.utils import is_file_readable

if TYPE_CHECKING:
    from io import BufferedIOBase
    from typing import Any

    from msl.io.types import PathLike, WriteLike


class HDF5Writer(Writer):
    """Writer for the [HDF5](https://www.hdfgroup.org/){:target="_blank"} file format.

    You can use this Writer as a [context manager][with]{:target="_blank"}, for example,

    ```python
    with HDF5Writer("my_file.h5") as root:
        root.create_dataset("dset", data=[1, 2, 3])
    ```

    This will automatically write `root` to the specified file when the [with][]{:target="_blank"}
    block exits.

    !!! info
        This Writer requires the [h5py](https://www.h5py.org/){:target="_blank"} package to be installed.
    """

    def write(  # noqa: C901, PLR0912, PLR0915
        self, file: PathLike | WriteLike | None = None, root: Group | None = None, **kwargs: Any
    ) -> None:
        """Write to a [HDF5](https://www.hdfgroup.org/){:target="_blank"} file.

        Args:
            file: The file to write a *root* to. If `None` then uses the value of
                `file` that was specified when [HDF5Writer][msl.io.writers.hdf5.HDF5Writer] was instantiated.
                If a file-like object, it must be open for writing in binary I/O and it must have `read`, `write`,
                `seek`, `tell`, `truncate` and `flush` methods.
            root: Write `root` in [HDF5](https://www.hdfgroup.org/){:target="_blank"} format.
                If `None` then write the [Group][msl.io.node.Group]s and [Dataset][msl.io.node.Dataset]s
                in the [HDF5Writer][msl.io.writers.hdf5.HDF5Writer] instance. This argument is useful when
                converting between different file formats.
            kwargs: All additional keyword arguments are passed to [h5py.File][]{:target="_blank"}.
        """
        if h5py is None:
            msg = "You must install h5py to write HDF5 files, run\n  pip install h5py"
            raise ImportError(msg)

        if file is None:
            file = self.file
        if not file:
            msg = "You must specify a file to write the root to"
            raise ValueError(msg)

        if root is None:
            root = self
        elif not isinstance(root, Group):  # pyright: ignore[reportUnnecessaryIsInstance]
            msg = "The root parameter must be a Group object"  # type: ignore[unreachable]  # pyright: ignore[reportUnreachable]
            raise TypeError(msg)

        if "mode" not in kwargs:
            kwargs["mode"] = "x"  # Create file, fail if exists

        @no_type_check
        def check_ndarray_dtype(obj: Any) -> Any:  # noqa: C901, PLR0911, PLR0912
            if not isinstance(obj, np.ndarray):
                return obj

            # h5py variable-length string
            v_str = h5py.special_dtype(vlen=str)

            if obj.dtype.names is not None:
                convert, dtype = False, []
                for n in obj.dtype.names:
                    typ = obj.dtype.fields[n][0]
                    if isinstance(obj[n].item(0), str):
                        dtype.append((n, v_str))
                        convert = True
                    else:
                        dtype.append((n, typ))
                if convert:
                    return obj.astype(dtype=dtype)
                return obj
            if obj.dtype.char == "U":
                return obj.astype(dtype=v_str)
            if obj.dtype.char == "O":
                has_complex = False
                for item in obj.flat:
                    if isinstance(item, str):
                        return obj.astype(dtype="S")
                    if isinstance(item, np.complexfloating):
                        has_complex = True
                    elif item is None:
                        return obj  # let h5py raise the error that HDF5 does not support NULL
                if has_complex:
                    return obj.astype(dtype=complex)
                return obj.astype(dtype=float)
            return obj

        def meta_to_dict(metadata: Metadata) -> dict[str, dict[str, Any] | Any]:
            return {
                k: meta_to_dict(v) if isinstance(v, Metadata) else check_ndarray_dtype(v) for k, v in metadata.items()
            }

        @no_type_check
        def h5_open(f: BufferedIOBase) -> None:
            with h5py.File(f, **kwargs) as h5:
                h5.attrs.update(**meta_to_dict(root.metadata))
                for name, value in root.items():
                    if self.is_dataset(value):
                        try:
                            vertex = h5.create_dataset(name, data=value.data)
                        except TypeError:
                            vertex = h5.create_dataset(name, data=check_ndarray_dtype(value.data))
                    else:
                        vertex = h5.create_group(name)
                    vertex.attrs.update(**meta_to_dict(value.metadata))

        # Calling h5py.File to write to a file on a mapped drive could raise
        # an OSError. This occurred when a local folder was shared and then
        # mapped on the same computer. Opening the file using open() and then
        # passing in the file handle to h5py.File is more universal
        if isinstance(file, (bytes, str, os.PathLike)):
            m = kwargs["mode"]
            if m in ["x", "w-"]:
                if os.path.isfile(file) or is_file_readable(file):  # noqa: PTH113
                    msg = f"File exists {file!r}\nSpecify mode='w' if you want to overwrite it."
                    raise FileExistsError(msg)
            elif m == "r+":
                if not (os.path.isfile(file) or is_file_readable(file)):  # noqa: PTH113
                    msg = f"File does not exist {file!r}"
                    raise FileNotFoundError(msg)
            elif m not in ["w", "a"]:
                msg = f"Invalid mode {m!r}"
                raise ValueError(msg)

            with open(file, mode="w+b") as fp:  # noqa: PTH123
                h5_open(fp)
        else:
            h5_open(file)
