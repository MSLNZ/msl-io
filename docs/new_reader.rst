.. _create-reader:

===================
Create a new Reader
===================

The following illustrates the basic requirements for creating a new Reader.

.. code-block:: python

   # import the necessary MSL-IO objects into your module
   from msl.io import register, Reader

   # register your Reader so that Python knows that your Reader exists
   @register.reader
   class AnExampleReader(Reader):
       """Name your class to be whatever you want, i.e., rename AnExampleReader"""

       def __init__(self, url, **kwargs):
           # Initialize the parent Reader class
           Reader.__init__(self, url)

           # **kwargs represent additional (and optional) key-value pairs that
           # a user can pass in to your Reader which you may need to know when
           # reading the data file

       @staticmethod
       def can_read(url):
           """This method answers the following question:

           Given a URL (which is a Python string that is the location to a file)
           can your Reader read this file?

           You must perform all the necessary checks that *uniquely* answers this
           question. For example, checking that the file extension is ".csv" is
           not unique enough.
           """
           return  # True or False

       def read(self):
           """This method reads the data file and returns a Dataset object."""

           # Create an empty dataset
           dataset = self.create_new_dataset()

           #
           # Populate the attributes of this `dataset` from the information in the file
           #

           # return the dataset
           return dataset

