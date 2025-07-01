# Release Notes

---

## unreleased

***Added:***

- support for Python 3.12 and 3.13
- [PEP-484](https://peps.python.org/pep-0484/) type annotations
- [GSheetsReader][msl.io.readers.gsheets.GSheetsReader] and [ExcelReader][msl.io.readers.excel.ExcelReader] can now be used as a context manager (includes the [GSheetsReader.close][msl.io.readers.gsheets.GSheetsReader.close] method)
- a `TEXT` member to the [GCellType][msl.io.google_api.GCellType] enum

***Changed:***

- convert to an implicit namespace package ([PEP-420](https://peps.python.org/pep-0420/))
- [utils.git_head][msl.io.utils.git_head] now returns a [GitHead][msl.io.utils.GitHead] dataclass with the `datetime` key replaced with a `timestamp` attribute
- the names of the keyword arguments to [utils.search][msl.io.utils.search]

***Removed:***

- support for Python &le; 3.8

## 0.1.0 (2023-06-16)

Initial release.
