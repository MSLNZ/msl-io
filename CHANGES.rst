=============
Release Notes
=============

Version 0.2.0 (in development)
==============================

* Added

  - :class:`~msl.io.readers.gsheets.GSheetsReader` and :class:`~msl.io.readers.excel.ExcelReader`
    can now be used as a context manager
  - :meth:`GSheetsReader.close <msl.io.readers.gsheets.GSheetsReader.close>` method
  - a *TEXT* member to the :class:`~msl.io.google_api.GCellType` enum

* Changed

   - `utils.git_head` now returns a `GitHead` dataclass with the `datetime` key replaced with a `timestamp` attribute
   - names of the keyword arguments to `utils.search`

* Removed

  - Support for Python 2.7, 3.5, 3.6 and 3.7

Version 0.1.0 (2023-06-16)
==========================
Initial release.

It is also the last release to support Python 2.7, 3.5, 3.6 and 3.7
