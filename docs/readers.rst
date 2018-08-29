.. _io-readers:

===========
MSL Readers
===========

The following :class:`~msl.io.reader.Reader`\'s are available:

.. toctree::

   DRS - Light Standards <_api/msl.io.readers.detector_responsivity_system>
   HDF5 <_api/msl.io.readers.hdf5>

.. _io-create-reader:

===================
Create a New Reader
===================
When adding a new MSL Reader class to the repository_ the following steps should be performed.
Please follow the `style guide`_.

.. note::
   If you do not want to upload the new MSL Reader class to the repository_ then you only need to
   write the code found in Step 2 to use your Reader in your own program. Once you import your
   module in your code your Reader will be available from the :func:`~msl.io.read` function.

1. Create a fork_ of the repository_.
2. Create a new Reader module by following this template and save it to the `msl/io/readers/`_ directory.

    .. code-block:: python

       # import the necessary MSL-IO objects
       from msl.io import register, Reader

       # register your Reader so that Python knows that your Reader exists
       @register
       class AnExampleReader(Reader):
           """Name your class to be whatever you want, i.e., change AnExampleReader"""

           def __init__(self, url, **kwargs):
               # Initialize the parent Reader class
               super(AnExampleReader, self).__init__(url)  # change AnExampleReader

               # **kwargs represent additional (and optional) key-value pairs that
               # a user can pass to your Reader class which you may need to know
               # when reading the data file

           @staticmethod
           def can_read(url):
               """This method answers the following question:

               Given a URL (which is a Python string that is the location of a file)
               can your Reader read this file?

               You must perform all the necessary checks that *uniquely* answers this
               question. For example, checking that the file extension is ".csv" is
               not unique enough.
               """
               return True or False

           def read(self):
               """This method reads the data file(s) and returns a Root object."""

               # Create the Root object
               # You can include key-value pairs to use as metadata for the Root
               root = self.create_root(**metadata)

               #
               # Populate the attributes of `root` from the information in the file(s)
               #

               # Return the Root object
               return root

3. Add an example data file to the `tests/samples`_ directory and add a test case to the `tests/`_ directory
   to make sure that your Reader is returned by calling the :func:`~msl.io.read` function using your example
   data file as the input and that the information in the returned object is correct. Run the tests using
   ``python setup.py tests`` (ideally you would run the tests for all
   :ref:`currently-supported versions <io-dependencies>` of Python, see also `test_envs.py`_).
4. Create a new ``msl.io.readers.<name of your module from Step 2>.rst`` file in `docs/_api`_. Follow the
   template that is used for the other ``.rst`` files in this directory.
5. Add the new Reader, alphabetically, to the ``.. toctree::`` in `docs/readers.rst`_. Follow the
   template that is used for the other Readers.
6. Add yourself to ``AUTHORS.rst`` and add a note in ``CHANGES.rst`` that you created this new Reader. These
   files are located in the root directory of the **MSL-IO** package.
7. Build the documentation running ``python setup.py docs`` (view the documentation by opening the
   ``docs/_build/html/index.html`` file).
8. If running the tests pass and building the documentation show no errors/warnings then create a `pull request`_.

.. _style guide: https://msl-package-manager.readthedocs.io/en/latest/developers_guide.html#edit-the-source-code-using-the-style-guide
.. _fork: https://help.github.com/articles/fork-a-repo/
.. _repository: https://github.com/MSLNZ/msl-io
.. _tests/samples: https://github.com/MSLNZ/msl-io/tree/master/tests/samples
.. _tests/: https://github.com/MSLNZ/msl-io/blob/master/tests/
.. _docs/_api: https://github.com/MSLNZ/msl-io/tree/master/docs/_api
.. _docs/readers.rst: https://github.com/MSLNZ/msl-io/blob/master/docs/readers.rst
.. _msl/io/readers/: https://github.com/MSLNZ/msl-io/tree/master/msl/io/readers
.. _pull request: https://help.github.com/articles/creating-a-pull-request-from-a-fork/
.. _test_envs.py: https://msl-package-manager.readthedocs.io/en/latest/new_package_readme.html#test-envs-py-commands
