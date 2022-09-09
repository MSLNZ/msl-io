.. _io-writers:

=======
Writers
=======

The following :class:`~msl.io.base.Writer`\s are available:

.. toctree::

   HDF5 <_api/msl.io.writers.hdf5>
   JSON <_api/msl.io.writers.json_>

.. _io-create-writer:

Create a New Writer
+++++++++++++++++++
When adding a new :class:`~msl.io.base.Writer` class to the repository_ the following
steps should be performed. Please follow the :ref:`style guide <style-guide>`.

1. Create a fork_ of the repository_.
2. Create a new :class:`~msl.io.base.Writer` by following this template and save it to
   the `msl/io/writers/`_ directory.

    .. code-block:: python

        # import the necessary MSL-IO objects
        from msl.io import Writer

        class MyExampleWriter(Writer):
            """Name your class to be whatever you want, i.e., change MyExampleWriter"""

            def write(self, file=None, root=None, **kwargs):
                """Implement your write method with the above signature.

                Parameters
                ----------
                file : path-like or file-like
                    The file to write to. If None then uses the value of
                    `file` that was specified when MyExampleWriter was instantiated.
                root : Root
                    Write `root` to the file. If None then write the Groups
                    and Datasets that were created using MyExampleWriter.
                **kwargs
                    Optional key-value pairs.
                """

3. Add test cases to the `tests/`_ directory to make sure that your Writer works as expected. It is
   recommended to try converting a :class:`~msl.io.base.Root` object between your Writer and other
   Writers that are available to verify different file-format conversions. Also, look at the test
   modules that begin with ``test_writer`` for more examples. Run the tests using ``python setup.py tests``
   (ideally you would run the tests for all :ref:`currently-supported versions <io-dependencies>` of
   Python, see also :ref:`create-readme-condatests`).
4. Create a new ``msl.io.writers.<name of your module from Step 2>.rst`` file in `docs/_api`_. Follow the
   template that is used for the other ``.rst`` files in this directory.
5. Add the new Writer, alphabetically, to the ``.. toctree::`` in `docs/writers.rst`_. Follow the
   template that is used for the other Writers.
6. Add the new Writer, alphabetically, to the ``.. autosummary::`` in `docs/api_docs.rst`_. Follow the
   template that is used for the other Writers.
7. Add yourself to ``AUTHORS.rst`` and add a note in ``CHANGES.rst`` that you created this new Writer. These
   files are located in the root directory of the **MSL-IO** package.
8. Build the documentation running ``python setup.py docs`` (view the documentation by opening the
   ``docs/_build/html/index.html`` file).
9. If running the tests pass and building the documentation show no errors/warnings then create a `pull request`_.

.. _fork: https://help.github.com/articles/fork-a-repo/
.. _repository: https://github.com/MSLNZ/msl-io
.. _tests/: https://github.com/MSLNZ/msl-io/blob/main/tests/
.. _docs/_api: https://github.com/MSLNZ/msl-io/tree/main/docs/_api
.. _docs/writers.rst: https://github.com/MSLNZ/msl-io/blob/main/docs/writers.rst
.. _docs/api_docs.rst: https://github.com/MSLNZ/msl-io/blob/main/docs/api_docs.rst
.. _msl/io/writers/: https://github.com/MSLNZ/msl-io/tree/main/msl/io/writers
.. _pull request: https://help.github.com/articles/creating-a-pull-request-from-a-fork/
