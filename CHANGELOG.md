# Release Notes

---

## unreleased

***Added:***

- [ODSReader][msl.io.readers.ods.ODSReader] for reading OpenDocument Spreadsheet files
- [GSheetsReader][msl.io.readers.gsheets.GSheetsReader] and [ExcelReader][msl.io.readers.excel.ExcelReader] can now be used as a context manager
- [PEP-484](https://peps.python.org/pep-0484/) type annotations
- a `TEXT` member to the [GCellType][msl.io.google_api.GCellType] enum
- support for Python 3.12 and 3.13

***Changed:***

- move the static `get_bytes`, `get_lines` and `get_extension` methods from the `Reader` class to the [utils][] module
- convert to an implicit namespace package ([PEP-420](https://peps.python.org/pep-0420/))
- [utils.git_head][msl.io.utils.git_head] now returns a [GitHead][msl.io.utils.GitHead] dataclass with the `datetime` key replaced with a `timestamp` attribute
- the names of the keyword arguments to [utils.search][msl.io.utils.search]

***Fixed:***

- specifying only the top-left cell to [read_table][msl.io.tables.read_table] returned the wrong cells from the spreadsheet

***Removed:***

- support for Python &le; 3.8

## 0.1.0 (2023-06-16)

Initial release.
