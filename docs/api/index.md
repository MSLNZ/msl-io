# API Overview

The following functions are available to read a file

* [read][msl.io.base.read] &mdash; Read a file that has a [Reader][msl-io-readers] subclass implemented
* [read_table][msl.io.read_table] &mdash; Read tabular data

The following classes are for reading cell values (not drawings or charts) in spreadsheets

* [ExcelReader][msl.io.readers.excel.ExcelReader] &mdash; Microsoft Excel
* [GSheetsReader][msl.io.readers.gsheets.GSheetsReader] &mdash; Google Sheets
* [ODSReader][msl.io.readers.ods.ODSReader] &mdash; OpenDocument Spreadsheet

These classes are for interacting with a Google account

* [GDrive][msl.io.google_api.GDrive] &mdash; Google Drive
* [GSheets][msl.io.google_api.GSheets] &mdash; Google Sheets
* [GMail][msl.io.google_api.GMail] &mdash; Google Mail

There are [Readers][msl-io-readers] and [Writers][msl-io-writers] and general helper (utility) functions are in the [utils][] module.
