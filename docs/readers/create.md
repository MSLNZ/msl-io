# Create a New Reader {: #msl-io-create-reader}

When adding a new [Reader][msl.io.base.Reader] to the [repository]{:target="_blank"} the following steps should be performed.

[uv]{:target="_blank"} is used as the package and project manager for `msl-io` development, it is recommended to install it.

!!! note
    If you do not want to contribute your new [Reader][msl.io.base.Reader] to the [repository]{:target="_blank"} then you only need to write the code shown in Step 2 to use your [Reader][msl.io.base.Reader] in your own software. Once you import your module in your code, your [Reader][msl.io.base.Reader] will be registered and it will be used to [read][msl.io.read] your data files.

1. Create a [fork]{:target="_blank"} of the [repository]{:target="_blank"}.

2. Create a new [Reader][msl.io.base.Reader] by following this template. Save it in the `src/msl/io/readers` folder.

    ```python
    from __future__ import annotations

    # It's a good idea to provide type annotations in your code
    from typing import TYPE_CHECKING

    # Import the necessary msl-io object to subclass
    from msl.io import Reader

    if TYPE_CHECKING:
        from typing import Any

        from msl.io.types import ReadLike


    # Sub-classing Reader will tell msl-io that your MyReader exists
    class MyReader(Reader):
        """Name your class to be whatever you want, i.e., change MyReader."""

        @staticmethod
        def can_read(file: ReadLike | str, **kwargs: Any) -> bool:
            """This method answers the following question:

            Given a file-like object (e.g., a file stream or a buffered reader)
            or a file path, can your Reader read this file?

            You must perform all the necessary checks that *uniquely* answers
            this question. For example, checking that the file extension is a
            particular value may not be unique enough.

            The optional kwargs can be passed in via the msl.io.read() function.

            This method must return a boolean:
            True (can read) or False (cannot read)
            """

        def read(self, **kwargs: Any) -> None:
            """This method reads the data file(s).

            The optional kwargs can be passed in via the msl.io.read() function.

            Your Reader class is a Root object.

            The file to read is available at self.file

            To add metadata to Root use self.add_metadata()

            To create a Group in Root use self.create_group()

            To create a Dataset in Root use self.create_dataset()

            This method should return None.
            """
    ```

3. Import your Reader in the `src/msl/io/readers/__init__.py` module. Follow what is done for the other Readers.

4. Add an example data file to the `tests/samples` directory and add a test case to the `tests` directory. Make sure that your Reader is returned by calling the [read][msl.io.base.read] function, using your example data file as the input, and that the information in the returned object is correct. Run the tests using `uv run pytest`.

5. Lint `uv run ruff check`, format `uv run ruff format` and type check `uv run basedpyright` the code.

6. Add the new Reader, alphabetically, to `docs/readers/index.md`. Follow what is done for the other Readers.

7. Update `CHANGELOG.md` stating that you added this new Reader.

8. Build the documentation `uv run mkdocs serve` and check that your Reader renders correctly.

9. If running the tests pass and linting, formatting, type checking and building the documentation do not show errors/warnings then create a [pull request]{:target="_blank"}.

[fork]: https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo
[pull request]: https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request-from-a-fork
[repository]: https://github.com/MSLNZ/msl-io
[uv]: https://docs.astral.sh/uv/
