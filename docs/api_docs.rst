.. _io-api:

========================
MSL-IO API Documentation
========================

The following functions are available to read a file

.. autosummary::

   ~msl.io.read
   ~msl.io.read_table
   ~msl.io.readers.excel.ExcelReader

the following classes are available as :ref:`io-writers`

.. autosummary::

   ~msl.io.writers.hdf5.HDF5Writer
   ~msl.io.writers.json_.JSONWriter

and general helper functions

.. autosummary::

   ~msl.io.utils.git_revision
   ~msl.io.utils.search
   ~msl.io.utils.send_email

Package Structure
-----------------

.. toctree::

   msl.io <_api/msl.io>
   msl.io.base_io <_api/msl.io.base_io>
   msl.io.constants <_api/msl.io.constants>
   msl.io.dataset <_api/msl.io.dataset>
   msl.io.dataset_logging <_api/msl.io.dataset_logging>
   msl.io.dictionary <_api/msl.io.dictionary>
   msl.io.group <_api/msl.io.group>
   msl.io.metadata <_api/msl.io.metadata>
   msl.io.tables <_api/msl.io.tables>
   msl.io.utils <_api/msl.io.utils>
   msl.io.vertex <_api/msl.io.vertex>
   msl.io.readers <_api/msl.io.readers>
   msl.io.writers <_api/msl.io.writers>

.. _HDF5: https://www.hdfgroup.org/
.. _JSON: https://www.json.org/
