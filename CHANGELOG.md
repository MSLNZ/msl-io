# Release Notes

---

## unreleased

***Added:***

- support for Python 3.14
- [RegularTransmittanceReader][msl.io.readers.spectrophotometer_trans_reader.RegularTransmittanceReader] for reading transmittance files from the MSL spectrophotometer

## 0.2.0 (2025-07-28)

***Added:***

- [read_table][msl.io.tables.read_table] supports `dtype="header"`
- the [dimensions][msl.io.readers.excel.ExcelReader.dimensions] method to [ExcelReader][msl.io.readers.excel.ExcelReader]
- the `merged` keyword argument to [Spreadsheet.read][msl.io.readers.spreadsheet.Spreadsheet.read]
- [ODSReader][msl.io.readers.ods.ODSReader] for reading OpenDocument Spreadsheet files
- [GSheetsReader][msl.io.readers.gsheets.GSheetsReader] and [ExcelReader][msl.io.readers.excel.ExcelReader] can now be used as a context manager
- [PEP-484](https://peps.python.org/pep-0484/) type annotations
- a `TEXT` member to the [GCellType][msl.io.google_api.GCellType] enum
- support for Python 3.12 and 3.13

***Changed:***

- implement the [\_\_init_subclass\_\_][object.__init_subclass__] method to register [Reader][msl.io.base.Reader] subclasses instead of using the `@register` decorator ([PEP-487](https://peps.python.org/pep-0487/))
- move the static `get_bytes`, `get_lines` and `get_extension` methods from the `Reader` class to the [utils][] module
- convert to an implicit namespace package ([PEP-420](https://peps.python.org/pep-0420/))
- [utils.git_head][msl.io.utils.git_head] now returns a [GitHead][msl.io.utils.GitHead] dataclass with the `datetime` key replaced with a `timestamp` attribute
- the names of the keyword arguments to [utils.search][msl.io.utils.search]

***Fixed:***

- specifying only the top-left cell to [read_table][msl.io.tables.read_table] returned the wrong cells from the spreadsheet

***Removed:***

- the `workbook` property to [ExcelReader][msl.io.readers.excel.ExcelReader]
- support for Python &le; 3.8

## 0.1.0 (2023-06-16)

Initial release.
