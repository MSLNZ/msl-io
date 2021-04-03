MSL-IO
======

|docs| |pypi| |travis| |appveyor|

**MSL-IO** follows the data model used by HDF5_ to read and write data files -- where there is a
Root_, Group_\s and Dataset_\s and these objects each have Metadata_ associated with them.

.. image:: https://raw.githubusercontent.com/MSLNZ/msl-io/master/docs/_static/hdf5_data_model.png

The tree structure is similar to the file-system structure used by operating systems. Group_\s
are analogous to the directories (where Root_ is the root Group_) and Dataset_\s are analogous
to the files.

The data files that can be read or created are not restricted to HDF5_ files, but any file format
that has a Reader_ implemented can be read and data files can be created using any of the Writer_\s.

Install
-------
To install **MSL-IO** run:

.. code-block:: console

   pip install msl-io

Alternatively, using the `MSL Package Manager`_ run:

.. code-block:: console

   msl install io

Dependencies
++++++++++++
* Python 2.7, 3.5+
* numpy_
* xlrd_
* google-api-python-client_
* google-auth-httplib2_
* google-auth-oauthlib_


Documentation
-------------
The documentation for **MSL-IO** can be found `here <https://msl-io.readthedocs.io/en/latest/index.html>`_.

.. |docs| image:: https://readthedocs.org/projects/msl-io/badge/?version=latest
   :target: https://msl-io.readthedocs.io/en/latest/
   :alt: Documentation Status
   :scale: 100%

.. |pypi| image:: https://badge.fury.io/py/msl-io.svg
   :target: https://badge.fury.io/py/msl-io

.. |travis| image:: https://img.shields.io/travis/MSLNZ/msl-io/master.svg?label=Travis-CI
   :target: https://travis-ci.org/MSLNZ/msl-io

.. |appveyor| image:: https://img.shields.io/appveyor/ci/jborbely/msl-io/master.svg?label=AppVeyor
   :target: https://ci.appveyor.com/project/jborbely/msl-io/branch/master

.. _HDF5: https://www.hdfgroup.org/
.. _Root: https://msl-io.readthedocs.io/en/latest/_api/msl.io.base_io.html#msl.io.base_io.Root
.. _Group: https://msl-io.readthedocs.io/en/latest/group.html
.. _Dataset: https://msl-io.readthedocs.io/en/latest/dataset.html
.. _Metadata: https://msl-io.readthedocs.io/en/latest/metadata.html
.. _Reader: https://msl-io.readthedocs.io/en/latest/readers.html
.. _Writer: https://msl-io.readthedocs.io/en/latest/writers.html
.. _MSL Package Manager: https://msl-package-manager.readthedocs.io/en/latest/
.. _numpy: https://www.numpy.org/
.. _xlrd: https://xlrd.readthedocs.io/en/latest/
.. _google-api-python-client: https://pypi.org/project/google-api-python-client/
.. _google-auth-httplib2: https://pypi.org/project/google-auth-httplib2/
.. _google-auth-oauthlib: https://pypi.org/project/google-auth-oauthlib/

