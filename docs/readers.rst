.. _io-readers:

=======
Readers
=======
The following :class:`~msl.io.base_io.Reader`\s are available:

.. toctree::

   DRS - Light Standards <_api/msl.io.readers.detector_responsivity_system>
   HDF5 <_api/msl.io.readers.hdf5>
   JSON <_api/msl.io.readers.json_>

.. _io-create-reader:

Create a New Reader
+++++++++++++++++++
When adding a new :class:`~msl.io.base_io.Reader` class to the repository_ the following
steps should be performed. Please follow the :ref:`style guide <style-guide>`.

.. note::
   If you do not want to upload the new :class:`~msl.io.base_io.Reader` class to the repository_
   then you only need to write the code found in Step 2 to use your :class:`~msl.io.base_io.Reader`
   in your own program. Once you import your module in your code your :class:`~msl.io.base_io.Reader`
   will be available from the :func:`~msl.io.read` function.

1. Create a fork_ of the repository_.
2. Create a new :class:`~msl.io.base_io.Reader` by following this template and save it to
   the `msl/io/readers/`_ directory.

    .. code-block:: python

       # import the necessary MSL-IO objects
       from msl.io import register, Reader

       # register your Reader so that Python knows that your Reader exists
       @register
       class AnExampleReader(Reader):
           """Name your class to be whatever you want, i.e., change AnExampleReader"""

           @staticmethod
           def can_read(file, **kwargs):
               """This method answers the following question:

               Given a path-like object (e.g., a string, bytes or os.PathLike object)
               that represents the location of a file or a file-like object (e.g., a
               stream, socket or in-memory buffer) can your Reader read this file?

               You must perform all the necessary checks that *uniquely* answers this
               question. For example, checking that the file extension is ".csv" is
               not unique enough.

               The optional kwargs can be passed in via the msl.io.read() method.

               This method must return a boolean: True (can read) or False (cannot read)
               """
               return boolean

           def read(self, **kwargs):
               """This method reads the data file(s).

               Your Reader class is a Root object. The optional kwargs can be
               passed in via the msl.io.read() method.

               The data file to read is available at self.file

               To add metadata to Root use self.add_metadata()

               To create a Group in Root use self.create_group()

               To create a Dataset in Root use self.create_dataset()

               This method should not return anything.
               """

3. Import your Reader in the ``msl/io/readers/__init__.py`` module.
4. Add an example data file to the `tests/samples`_ directory and add a test case to the `tests/`_ directory
   to make sure that your Reader is returned by calling the :func:`~msl.io.read` function using your example
   data file as the input and that the information in the returned object is correct. Run the tests using
   ``python setup.py tests`` (ideally you would run the tests for all
   :ref:`currently-supported versions <io-dependencies>` of Python, see also :ref:`create-readme-condatests`).
5. Create a new ``msl.io.readers.<name of your module from Step 2>.rst`` file in `docs/_api`_. Follow the
   template that is used for the other ``.rst`` files in this directory.
6. Add the new Reader, alphabetically, to the ``.. toctree::`` in `docs/readers.rst`_. Follow the
   template that is used for the other Readers.
7. Add yourself to ``AUTHORS.rst`` and add a note in ``CHANGES.rst`` that you created this new Reader. These
   files are located in the root directory of the **MSL-IO** package.
8. Build the documentation running ``python setup.py docs`` (view the documentation by opening the
   ``docs/_build/html/index.html`` file).
9. If running the tests pass and building the documentation show no errors/warnings then create a `pull request`_.

.. _fork: https://help.github.com/articles/fork-a-repo/
.. _repository: https://github.com/MSLNZ/msl-io
.. _tests/samples: https://github.com/MSLNZ/msl-io/tree/main/tests/samples
.. _tests/: https://github.com/MSLNZ/msl-io/blob/main/tests/
.. _docs/_api: https://github.com/MSLNZ/msl-io/tree/main/docs/_api
.. _docs/readers.rst: https://github.com/MSLNZ/msl-io/blob/main/docs/readers.rst
.. _msl/io/readers/: https://github.com/MSLNZ/msl-io/tree/main/msl/io/readers
.. _pull request: https://help.github.com/articles/creating-a-pull-request-from-a-fork/
