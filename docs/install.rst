.. _io-install:

Install MSL-IO
==============

To install **MSL-IO** run

.. code-block:: console

   pip install msl-io

Alternatively, using the `MSL Package Manager`_ run

.. code-block:: console

   msl install io

.. _io-dependencies:

Dependencies
------------
* Python 3.8+
* numpy_
* xlrd_ (bundled with **MSL-IO**)

Optional Dependencies
---------------------
The following packages are not automatically installed when **MSL-IO**
is installed but may be required to read some data files.

* h5py_
* google-api-python-client_
* google-auth-httplib2_
* google-auth-oauthlib_

To include h5py when installing **MSL-IO** run

.. code-block:: console

   msl install io[h5py]

To include the Google-API packages when installing **MSL-IO** run

.. code-block:: console

   msl install io[google]

.. _MSL Package Manager: https://msl-package-manager.readthedocs.io/en/stable/
.. _numpy: https://www.numpy.org/
.. _h5py: https://www.h5py.org/
.. _xlrd: https://xlrd.readthedocs.io/en/stable/
.. _google-api-python-client: https://pypi.org/project/google-api-python-client/
.. _google-auth-httplib2: https://pypi.org/project/google-auth-httplib2/
.. _google-auth-oauthlib: https://pypi.org/project/google-auth-oauthlib/
