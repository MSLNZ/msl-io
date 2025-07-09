# Create a New Writer {: #msl-io-create-writer}

When adding a new [Writer][msl.io.base.Writer] to the [repository]{:target="_blank"} the following steps should be performed. You will also need to [Create a New Reader][msl-io-create-reader].

[uv]{:target="_blank"} is used as the package and project manager for `msl-io` development, it is recommended to install it.

1. Create a [fork]{:target="_blank"} of the [repository]{:target="_blank"}.

2. Create a new [Writer][msl.io.base.Writer] by following this template. Save it in the `src/msl/io/writers` folder.

    ```python
    from __future__ import annotations

    # It's a good idea to provide type annotations in your code
    from typing import TYPE_CHECKING

    # Import the necessary msl-io objects
    from msl.io import Writer

    if TYPE_CHECKING:
        from typing import Any

        from msl.io import Group
        from msl.io.types import PathLike, WriteLike


    class MyWriter(Writer):
        """Name your class to be whatever you want, i.e., change MyWriter."""

        def write(
            self, file: PathLike | WriteLike | None = None, root: Group | None = None, **kwargs: Any
        ) -> None:
            """Implement your write method with the above signature.

            Args:
                file: The file to write to. If `None` then uses the value of
                    `file` that was specified when `MyWriter` was instantiated.
                root: Write `root` to the file. If None then write the Groups
                    and Datasets that were created using `MyWriter`.
                kwargs: Optional keyword arguments.
            """
    ```

3. Import your Writer in the `src/msl/io/writers/__init__.py` and `src/msl/io/__init__.py` modules. Follow what is done for the other Writers.

4. Add test cases to the `tests` directory to make sure that your Writer works as expected. It is recommended to try converting a [Root][msl.io.base.Root] object between your Writer and other Writers that are available to verify different file-format conversions. Also, look at the test modules that begin with `test_writer` for more examples. Run the tests using `uv run pytest`.

5. Lint `uv run ruff check`, format `uv run ruff format` and type check `uv run basedpyright` the code.

6. Add the new Writer, alphabetically, to `docs/writers/index.md`. Follow what is done for the other Writers.

7. Update `CHANGELOG.md` stating that you added this new Writer.

8. Build the documentation `uv run mkdocs serve` and check that your Writer renders correctly.

9. If running the tests pass and linting, formatting, type checking and building the documentation do not show errors/warnings then create a [pull request]{:target="_blank"}.

[fork]: https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo
[pull request]: https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request-from-a-fork
[repository]: https://github.com/MSLNZ/msl-io
[uv]: https://docs.astral.sh/uv/
