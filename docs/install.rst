.. _io-install:

Install MSL-IO
==============

To install **MSL-IO** run:

.. code-block:: console

   pip install msl-io

Alternatively, using the `MSL Package Manager`_ run:

.. code-block:: console

   msl install io

.. _io-dependencies:

Dependencies
------------
* Python 2.7, 3.5+
* numpy_
* xlrd_
* google-api-python-client_
* google-auth-httplib2_
* google-auth-oauthlib_

Optional Dependencies
---------------------
The following packages are not automatically installed when **MSL-IO** is installed but may be
required to read some data files.

* h5py_ -- to include it automatically when installing **MSL-IO** run ``msl install io[h5py]``


.. _MSL Package Manager: https://msl-package-manager.readthedocs.io/en/latest/
.. _numpy: https://www.numpy.org/
.. _h5py: https://www.h5py.org/
.. _xlrd: https://xlrd.readthedocs.io/en/latest/
.. _google-api-python-client: https://pypi.org/project/google-api-python-client/
.. _google-auth-httplib2: https://pypi.org/project/google-auth-httplib2/
.. _google-auth-oauthlib: https://pypi.org/project/google-auth-oauthlib/
