from __future__ import annotations

import json
from io import BufferedIOBase
from typing import TYPE_CHECKING

import numpy as np

from msl.io.base import Reader
from msl.io.utils import get_bytes, get_lines

if TYPE_CHECKING:
    from typing import Any

    from msl.io.node import Group
    from msl.io.types import ReadLike


class JSONReader(Reader):
    """Read a file that was created by [JSONWriter][msl.io.writers.json_.JSONWriter]."""

    @staticmethod
    def can_read(file: ReadLike | str, **kwargs: Any) -> bool:
        """Checks if the file was created by [JSONWriter][msl.io.writers.json_.JSONWriter].

        Args:
            file: The file to check.
            kwargs: All keyword arguments are passed to [get_lines][msl.io.utils.get_lines].

        Returns:
            Whether the text `MSL JSONWriter` is in the first line of the file.
        """
        text: bytes | str
        if isinstance(file, (str, BufferedIOBase)):
            text = get_bytes(file, 21, 34)
        else:
            text = get_lines(file, 1, **kwargs)[0][20:34]

        if isinstance(text, str):
            text = text.encode()
        return text == b"MSL JSONWriter"

    def read(self, **kwargs: Any) -> None:  # noqa: C901
        """Read the file that was created by [JSONWriter][msl.io.writers.json_.JSONWriter].

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

        if isinstance(self.file, str):
            with open(self.file, mode="rt", **open_kwargs) as fp:  # noqa: PTH123, UP015
                _ = fp.readline()  # skip the first line
                dict_ = json.loads(fp.read(), **kwargs)
        else:
            _ = self.file.readline()  # skip the first line
            data = self.file.read()
            if isinstance(data, bytes):
                data = data.decode(**open_kwargs)
            dict_ = json.loads(data, **kwargs)

        def create_group(parent: Group | None, name: str, node: dict[str, Any]) -> None:
            group = self if parent is None else parent.create_group(name)
            for key, value in node.items():
                if not isinstance(value, dict):  # Metadata
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
                            kws[d_key] = d_val
                    _ = group.create_dataset(key, **kws)
                else:  # use recursion to create a sub-Group
                    create_group(group, key, value)  # pyright: ignore[reportUnknownArgumentType]

        # create the root group
        create_group(None, "", dict_)
