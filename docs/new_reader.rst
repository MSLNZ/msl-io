.. _create-reader:

===================
Create a New Reader
===================

The following illustrates the basic requirements for creating a new :class:`~msl.io.reader.Reader`.

.. code-block:: python

   # import the necessary MSL-IO objects
   from msl.io import register, Reader

   # register your Reader so that Python knows that your Reader exists
   @register.reader
   class AnExampleReader(Reader):
       """Name your class to be whatever you want, i.e., rename AnExampleReader"""

       def __init__(self, url, **kwargs):
           # Initialize the parent Reader class
           super(AnExampleReader, self).__init__(url)

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


Once you create a new :class:`~msl.io.reader.Reader` you must add an example data file to
the ``tests/examples/`` directory and add a test case to ``tests/test_read.py``.
