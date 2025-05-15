"""
Constants used by MSL-IO.
"""
import os

# If this module is run via "sudo python" on a Raspberry Pi the value of
# os.path.expanduser('~') becomes '/root' instead of '/home/pi'. On Linux using
# "sudo python" keeps os.path.expanduser('~') as /home/<username> and running this
# module in an elevated command prompt on Windows keeps os.path.expanduser('~')
# as C:\\Users\\<username>. Therefore defining USER_DIR in the following way keeps
# things more consistent across more platforms.
USER_DIR = os.path.expanduser('~'+os.getenv('SUDO_USER', ''))

HOME_DIR = os.getenv('MSL_IO_HOME', os.path.join(USER_DIR, '.msl', 'io'))
""":class:`str`: The default directory where all files that are used by MSL-IO are located.

Can be overwritten by specifying a ``MSL_IO_HOME`` environment variable.
"""
