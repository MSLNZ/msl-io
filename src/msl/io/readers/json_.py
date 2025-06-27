"""Read a file that was created by [JSONWriter][msl.io.writers.json_.JSONWriter]."""

from __future__ import annotations

import json
import os
from io import BufferedIOBase
from typing import TYPE_CHECKING

import numpy as np

from msl.io.base import Reader, register

if TYPE_CHECKING:
    from typing import IO, Any

    from numpy.typing import ArrayLike, NDArray

    from msl.io._types import PathLike
    from msl.io.node import Dataset, Group


@register
class JSONReader(Reader):
    """Read a file that was created by [JSONWriter][msl.io.writers.json_.JSONWriter]."""

    @staticmethod
    def can_read(file: IO[str] | IO[bytes] | PathLike, **kwargs: Any) -> bool:
        """Checks if the text `MSL JSONWriter` is in the first line of the file..

        Args:
            file: The file to check.
            kwargs: All keyword arguments are passed to [get_lines][msl.io.base.Reader.get_lines].
        """
        if isinstance(file, (bytes, str, os.PathLike, BufferedIOBase)):
            text = Reader.get_bytes(file, 21, 34)
        else:
            text = Reader.get_lines(file, 1, **kwargs)[0][20:34]

        if isinstance(text, bytes):
            text = text.decode()
        return text == "MSL JSONWriter"

    def read(self, **kwargs: Any) -> None:  # noqa: C901
        """Read the file that was created by [JSONWriter][msl.io.writers.json_.JSONWriter].

        If a [Metadata][msl.io.metadata.Metadata] `key` has a `value` that is a
        [list][] then the list is converted to an [numpy.ndarray][] with [numpy.dtype][] as [object][].

        Args:
            kwargs:  Accepts `encoding` and `errors` keyword arguments which are passed to
                [open][]. The default `encoding` value is `utf-8` and the default
                `errors` value is `strict`. All additional keyword arguments are passed to
                [json.loads][].
        """
        open_kwargs = {
            "encoding": kwargs.get("encoding", "utf-8"),
            "errors": kwargs.pop("errors", "strict"),
        }

        if isinstance(self.file, (bytes, str, os.PathLike)):
            with open(self.file, mode="rt", **open_kwargs) as fp:  # noqa: PTH123, UP015
                _ = fp.readline()  # skip the first line
                dict_ = json.loads(fp.read(), **kwargs)
        elif self.file is not None:
            _ = self.file.readline()  # skip the first line
            data = self.file.read()
            if isinstance(data, bytes):
                data = data.decode(**open_kwargs)
            dict_ = json.loads(data, **kwargs)
        else:
            msg = f"Should never get here, file type is {type(self.file)}"
            raise TypeError(msg)

        def list_to_ndarray(list_: ArrayLike) -> NDArray[Any]:
            # convert a Metadata value to ndarray because one can easily make ndarray read only
            # use dtype=object because it guarantees that the data types are preserved
            # for example,
            #   >>> a = np.asarray([True, -5, 0.002345, 'something', 49.1871524])
            #   >>> a
            #   array(['True', '-5', '0.002345', 'something', '49.1871524'], dtype='<U32')  # noqa: ERA001
            # would cast every element to a string
            # also a regular Python list stores items as objects
            return np.asarray(list_, dtype=object)

        def create_group(parent: Group | None, name: str, node: Group | Dataset) -> None:
            group = self if parent is None else parent.create_group(name)
            for key, value in node.items():
                if not isinstance(value, dict):  # Metadata
                    if isinstance(value, list):
                        value = list_to_ndarray(value)  # pyright: ignore[reportUnknownArgumentType]  # noqa: PLW2901
                    group.metadata[key] = value
                elif "dtype" in value and "data" in value:  # Dataset
                    kws: dict[str, Any] = {}
                    for d_key, d_val in value.items():  # pyright: ignore[reportUnknownVariableType]
                        if d_key == "data":
                            pass  # handled in the 'dtype' check
                        elif d_key == "dtype":
                            if isinstance(d_val, list):
                                kws["data"] = np.asarray(
                                    [tuple(row) for row in value["data"]],  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
                                    dtype=[tuple(item) for item in d_val],  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
                                )
                            else:
                                kws["data"] = np.asarray(value["data"], dtype=d_val)  # pyright: ignore[reportUnknownArgumentType]
                        else:  # Metadata
                            if isinstance(d_val, list):
                                d_val = list_to_ndarray(d_val)  # pyright: ignore[reportUnknownArgumentType]  # noqa: PLW2901
                            kws[d_key] = d_val
                    _ = group.create_dataset(key, **kws)
                else:  # use recursion to create a sub-Group
                    create_group(group, key, value)  # pyright: ignore[reportArgumentType]

        # create the root group
        create_group(None, "", dict_)
