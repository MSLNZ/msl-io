.. _io-install:

Install MSL-IO
==============

To install **MSL-IO** run:

.. code-block:: console

   pip install https://github.com/MSLNZ/msl-io/archive/master.zip

Alternatively, using the `MSL Package Manager`_ run:

.. code-block:: console

   msl install io

.. _io-dependencies:

Dependencies
------------
* Python 2.7, 3.5+
* numpy_
* xlrd_

Optional Dependencies
---------------------
The following packages are not automatically installed when **MSL-IO** is installed but may be
required to read some data files.

* h5py_ -- to include it automatically when installing **MSL-IO** run ``msl install io[h5py]``


.. _MSL Package Manager: https://msl-package-manager.readthedocs.io/en/latest/
.. _numpy: https://www.numpy.org/
.. _h5py: https://www.h5py.org/
.. _xlrd: https://xlrd.readthedocs.io/en/latest/
