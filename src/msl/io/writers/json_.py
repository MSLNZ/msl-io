from __future__ import annotations

import json
import os
from io import BufferedIOBase
from typing import TYPE_CHECKING, no_type_check

import numpy as np

from msl.io.base import Writer
from msl.io.metadata import Metadata
from msl.io.node import Group
from msl.io.utils import is_file_readable

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import IO, Any, Callable

    from msl.io._types import PathLike
    from msl.io.node import Dataset


class JSONWriter(Writer):
    """Writer for a [JSON](https://www.json.org/) file format.

    You can use this Writer as a [context manager][with]{:target="_blank"}, for example,

    ```python
    with JSONWriter("my_file.json") as root:
        root.update_context_kwargs(indent=4)
        dset = root.create_dataset("dset", data=[1, 2, 3])
    ```

    This will automatically write `root` to the specified file using four spaces as the indentation
    level (instead of the default value of two spaces) when the [with][]{:target="_blank"} block exits.
    """

    def write(  # noqa: C901, PLR0912, PLR0915
        self, file: IO[str] | IO[bytes] | PathLike | None = None, root: Group | None = None, **kwargs: Any
    ) -> None:
        """Write to a [JSON](https://www.json.org/){:target="_blank"} file.

        The first line in the output file contains a description that the file was created by the
        [JSONWriter][msl.io.writers.json_.JSONWriter]. It begins with a `#` and contains a version number.

        Version 1.0 specifications:

        * Use the *dtype* and *data* keys to uniquely identify a
          [JSON](https://www.json.org/){:target="_blank"} object as a [Dataset][msl.io.node.Dataset].

        * If a [Metadata][msl.io.metadata.Metadata] *key* has a *value* that is a
          [Metadata][msl.io.metadata.Metadata] object then the *key* becomes the name
          of a [Group][msl.io.node.Group] and the *value* becomes
          [Metadata][msl.io.metadata.Metadata] of that [Group][msl.io.node.Group].

        Args:
            file: The file to write a *root* to. If `None` then uses the value of
                `file` that was specified when [JSONWriter][msl.io.writers.json_.JSONWriter] was instantiated.
            root: Write `root` in [JSON](https://www.json.org/){:target="_blank"} format.
                If `None` then write the [Group][msl.io.node.Group]s and [Dataset][msl.io.node.Dataset]s
                in the Writer instance. This argument is useful when converting between different file formats.
            kwargs: Accepts `mode`, `encoding` and `errors` keyword arguments which are passed
                to [open][]{:target="_blank"}. The default `encoding` value is `utf-8` and the default
                `errors` value is `strict`. All additional keyword arguments are passed to
                [json.dump][]{:target="_blank"}. The default indentation level is `2`.
        """
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

        def add_dataset(d: dict[str, Any], dataset: Dataset) -> None:
            if dataset.dtype.fields:
                d["dtype"] = np.array([[name, str(dtype)] for name, (dtype, _) in dataset.dtype.fields.items()])
            else:
                d["dtype"] = dataset.dtype.str
            d["data"] = dataset.data

        def meta_to_dict(metadata: Metadata) -> dict[str, dict[str, Any] | Any]:
            return {k: meta_to_dict(v) if isinstance(v, Metadata) else v for k, v in metadata.items()}

        dict_ = dict(**meta_to_dict(root.metadata))

        for name, value in root.items():
            nodes = name.split("/")
            root_key = nodes[1]

            if root_key not in dict_:
                dict_[root_key] = dict(**meta_to_dict(value.metadata))
                if root.is_dataset(value):
                    add_dataset(dict_[root_key], value)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]

            if len(nodes) > 2:  # noqa: PLR2004
                vertex = dict_[root_key]
                for key in nodes[2:-1]:
                    vertex = vertex[key]

                leaf_key = nodes[-1]
                if leaf_key not in vertex:
                    vertex[leaf_key] = dict(**meta_to_dict(value.metadata))
                    if root.is_dataset(value):
                        add_dataset(vertex[leaf_key], value)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]

        open_kwargs = {
            "mode": kwargs.pop("mode", None),
            "encoding": kwargs.pop("encoding", "utf-8"),
            "errors": kwargs.pop("errors", "strict"),
        }

        if isinstance(file, (bytes, str, os.PathLike)):
            if not open_kwargs["mode"]:
                open_kwargs["mode"] = "w"
                if os.path.isfile(file) or is_file_readable(file):  # noqa: PTH113
                    msg = f"File exists {file!r}\nSpecify mode='w' if you want to overwrite it."
                    raise FileExistsError(msg)
            elif open_kwargs["mode"] == "r":
                msg = f"Invalid mode {open_kwargs['mode']!r}"
                raise ValueError(msg)
            elif open_kwargs["mode"] == "a":
                open_kwargs["mode"] = "w"

        if "indent" not in kwargs:
            kwargs["indent"] = 2
        if "cls" not in kwargs:
            kwargs["cls"] = _NumpyEncoder

        # header => '#File created with: MSL {} version 1.0\n'.format(self.__class__.__name__)
        #
        # Don't use the above definition of 'header' since JSONWriter could be sub-classed
        # and therefore the value of self.__class__.__name__ would change. The
        # JSONReader.can_read() method expects the text 'MSL JSONWriter' to be in a
        # specific location on the first line in the file.
        header = "#File created with: MSL JSONWriter version 1.0\n"

        if isinstance(file, (bytes, str, os.PathLike)):
            with open(file, **open_kwargs) as fp:  # pyright: ignore[reportUnknownVariableType]  # noqa: PTH123
                _ = fp.write(header)  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
                json.dump(dict_, fp, **kwargs)  # pyright: ignore[reportUnknownArgumentType]
        elif isinstance(file, BufferedIOBase):
            encoding = open_kwargs["encoding"]
            _ = file.write(header.encode(encoding))  # pyright: ignore[reportArgumentType]
            _ = file.write(json.dumps(dict_, **kwargs).encode(encoding))  # pyright: ignore[reportArgumentType]
        else:
            _ = file.write(header)  # type: ignore[call-overload]  # pyright: ignore[reportArgumentType, reportCallIssue, reportUnknownVariableType]
            json.dump(dict_, file, **kwargs)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]


INFINITY = float("inf")


class _NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder that writes a 1-dimensional list on a single line and handles numpy objects."""

    @no_type_check
    def iterencode(self, o: object, _one_shot: bool = False) -> Iterator[str]:  # noqa: FBT001, FBT002
        """Essentially a copy-paste from the builtin method, except _one_shot is assumed to be False."""
        markers = {} if self.check_circular else None
        _encoder = json.encoder.encode_basestring_ascii if self.ensure_ascii else json.encoder.encode_basestring

        def float_str(
            o: float,
            allow_nan: bool = self.allow_nan,  # noqa: FBT001
            _repr: Callable[[float], str] = float.__repr__,
            _inf: float = INFINITY,
            _neginf: float = -INFINITY,
        ) -> str:
            # Check for specials.  Note that this type of test is processor
            # and/or platform-specific, so do tests which don't depend on the
            # internals.

            if o != o:  # noqa: PLR0124
                text = "NaN"
            elif o == _inf:
                text = "Infinity"
            elif o == _neginf:
                text = "-Infinity"
            else:
                return _repr(o)

            if not allow_nan:
                msg = f"Out of range float values are not JSON compliant: {o!r}"
                raise ValueError(msg)

            return text

        _iterencode = _make_iterencode(
            markers=markers,
            _default=self.default,
            _encoder=_encoder,
            _indent=self.indent if self.indent is None or isinstance(self.indent, str) else " " * self.indent,
            _float_str=float_str,
            _key_separator=self.key_separator,
            _item_separator=self.item_separator,
            _sort_keys=self.sort_keys,
            _skip_keys=self.skipkeys,
        )
        return _iterencode(o, 0)

    def default(self, o: object) -> Any:
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, np.integer):
            return int(o)  # pyright: ignore[reportUnknownArgumentType]
        if isinstance(o, np.floating):
            return float(o)  # pyright: ignore[reportUnknownArgumentType]
        if isinstance(o, np.bool_):
            return bool(o)
        if isinstance(o, bytes):
            return o.decode(encoding="utf-8")
        return super().default(o)


@no_type_check
def _make_iterencode(  # noqa: C901, PLR0913, PLR0915
    *,
    markers: dict[Any, Any] | None,
    _default: Callable[[object], Any],
    _encoder: Callable[[str], str],
    _indent: str | None,
    _float_str: Callable[[float], str],
    _key_separator: str,
    _item_separator: str,
    _sort_keys: bool,
    _skip_keys: bool,
    ## HACK: hand-optimized bytecode; turn globals into locals  # noqa: FIX004
    ValueError=ValueError,  # noqa: A002, ANN001, N803
    dict=dict,  # noqa: A002, ANN001
    float=float,  # noqa: A002, ANN001
    id=id,  # noqa: A002, ANN001
    int=int,  # noqa: A002, ANN001
    isinstance=isinstance,  # noqa: A002, ANN001
    list=list,  # noqa: A002, ANN001
    str=str,  # noqa: A002, ANN001
    tuple=tuple,  # noqa: A002, ANN001
    _int_str=int.__repr__,  # noqa: ANN001
) -> Callable[..., Iterator[str]]:
    """Essentially a copy-paste from the builtin function, except for a custom __indent variable in _iterencode_list."""

    @no_type_check
    def _iterencode_list(lst: list[Any], _current_indent_level: int) -> Iterator[str]:  # noqa: C901, PLR0912, PLR0915
        if not lst:
            yield "[]"
            return
        if markers is not None:
            marker_id = id(lst)
            if marker_id in markers:
                msg = "Circular reference detected"
                raise ValueError(msg)
            markers[marker_id] = lst

        ################ Custom implementation ##################
        def dim(a: list[Any]) -> None:
            if isinstance(a, (list, tuple)):
                shape.append(len(a))
                dim(a[0])

        shape: list[Any] = []
        dim(lst)
        # create a new __indent variable and use it for the rest
        # of the _iterencode_list function
        __indent = None if len(shape) == 1 else _indent
        #########################################################

        buf = "["
        if __indent is not None:
            _current_indent_level += 1
            newline_indent = "\n" + __indent * _current_indent_level
            separator = _item_separator + newline_indent
            buf += newline_indent
        else:
            newline_indent = None
            separator = _item_separator
        first = True
        for value in lst:
            if first:
                first = False
            else:
                buf = separator
            if isinstance(value, str):
                yield buf + _encoder(value)
            elif value is None:
                yield buf + "null"
            elif value is True:
                yield buf + "true"
            elif value is False:
                yield buf + "false"
            elif isinstance(value, int):
                # Subclasses of int/float may override __repr__, but we still
                # want to encode them as integers/floats in JSON. One example
                # within the standard library is IntEnum.
                yield buf + _int_str(value)
            elif isinstance(value, float):
                # see comment above for int
                yield buf + _float_str(value)
            else:
                yield buf
                if isinstance(value, (list, tuple)):
                    chunks = _iterencode_list(value, _current_indent_level)
                elif isinstance(value, dict):
                    chunks = _iterencode_dict(value, _current_indent_level)
                else:
                    chunks = _iterencode(value, _current_indent_level)
                yield from chunks
        if newline_indent is not None:
            _current_indent_level -= 1
            yield "\n" + __indent * _current_indent_level
        yield "]"
        if markers is not None:
            del markers[marker_id]

    @no_type_check
    def _iterencode_dict(dct, _current_indent_level):  # noqa: ANN001, ANN202, C901, PLR0912, PLR0915
        if not dct:
            yield "{}"
            return
        if markers is not None:
            marker_id = id(dct)
            if marker_id in markers:
                msg = "Circular reference detected"
                raise ValueError(msg)
            markers[marker_id] = dct
        yield "{"
        if _indent is not None:
            _current_indent_level += 1
            newline_indent = "\n" + _indent * _current_indent_level
            item_separator = _item_separator + newline_indent
        else:
            newline_indent = None
            item_separator = _item_separator
        first = True
        items = sorted(dct.items()) if _sort_keys else dct.items()
        for key, value in items:
            if isinstance(key, str):
                pass
            # JavaScript is weakly typed for these, so it makes sense to
            # also allow them.  Many encoders seem to do something like this.
            elif isinstance(key, float):
                # see comment for int/float in _make_iterencode
                key = _float_str(key)  # noqa: PLW2901
            elif key is True:
                key = "true"  # noqa: PLW2901
            elif key is False:
                key = "false"  # noqa: PLW2901
            elif key is None:
                key = "null"  # noqa: PLW2901
            elif isinstance(key, int):
                # see comment for int/float in _make_iterencode
                key = _int_str(key)  # noqa: PLW2901
            elif _skip_keys:
                continue
            else:
                msg = f"keys must be str, int, float, bool or None, not {key.__class__.__name__}"
                raise TypeError(msg)
            if first:
                first = False
                if newline_indent is not None:
                    yield newline_indent
            else:
                yield item_separator
            yield _encoder(key)
            yield _key_separator
            if isinstance(value, str):
                yield _encoder(value)
            elif value is None:
                yield "null"
            elif value is True:
                yield "true"
            elif value is False:
                yield "false"
            elif isinstance(value, int):
                # see comment for int/float in _make_iterencode
                yield _int_str(value)
            elif isinstance(value, float):
                # see comment for int/float in _make_iterencode
                yield _float_str(value)
            else:
                if isinstance(value, (list, tuple)):
                    chunks = _iterencode_list(value, _current_indent_level)
                elif isinstance(value, dict):
                    chunks = _iterencode_dict(value, _current_indent_level)
                else:
                    chunks = _iterencode(value, _current_indent_level)
                yield from chunks
        if not first and newline_indent is not None:
            _current_indent_level -= 1
            yield "\n" + _indent * _current_indent_level
        yield "}"
        if markers is not None:
            del markers[marker_id]

    @no_type_check
    def _iterencode(o: object, _current_indent_level: int) -> Iterator[str]:  # noqa: C901
        if isinstance(o, str):
            yield _encoder(o)
        elif o is None:
            yield "null"
        elif o is True:
            yield "true"
        elif o is False:
            yield "false"
        elif isinstance(o, int):
            # see comment for int/float in _make_iterencode
            yield _int_str(o)
        elif isinstance(o, float):
            # see comment for int/float in _make_iterencode
            yield _float_str(o)
        elif isinstance(o, (list, tuple)):
            yield from _iterencode_list(o, _current_indent_level)
        elif isinstance(o, dict):
            yield from _iterencode_dict(o, _current_indent_level)
        else:
            if markers is not None:
                marker_id = id(o)
                if marker_id in markers:
                    msg = "Circular reference detected"
                    raise ValueError(msg)
                markers[marker_id] = o
            o = _default(o)
            yield from _iterencode(o, _current_indent_level)
            if markers is not None:
                del markers[marker_id]

    return _iterencode
