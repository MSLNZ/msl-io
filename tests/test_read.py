# -*- coding: utf-8 -*-
import time
import socket
import threading
from io import BytesIO

import pytest

from msl.io import read, JSONWriter
from msl.io.readers import JSONReader

from helper import read_sample


def test_raises_ioerror():

    # file does not exist
    with pytest.raises(IOError) as e:
        read('does_not.exist')
    assert 'File does not exist' in str(e.value)

    # no Reader class exists to read this test_read.py file
    with pytest.raises(IOError) as e:
        read(__file__)
    assert 'No Reader exists' in str(e.value)


def test_unicode_filename():
    with pytest.raises(IOError) as e:
        read_sample(u'Filé döes ñot éxist')
    assert 'File does not exist' in str(e.value)

    with pytest.raises(IOError) as e:
        read_sample(u'uñicödé')
    assert 'No Reader exists' in str(e.value)

    root = read_sample(u'uñicödé.h5')
    assert root.metadata.is_unicode
    assert root.file.endswith(u'uñicödé.h5')
    assert u'café' in root
    assert u'/café' in root
    assert u'café/caña' in root
    assert u'/café/caña' in root
    assert u'caña' in root[u'café']
    assert u'/caña' in root[u'/café']
    assert u'cafécaña' not in root


def test_read_from_socket():
    # test that we can read/write a Root object from a socket stream

    # get any available port
    sock = socket.socket()
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()

    # the server will run in a separate thread
    def start_server():
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('localhost', port))
        server.listen(1)
        conn, _ = server.accept()
        with BytesIO(conn.recv(2**18)) as buf:
            # check that the bytes from the client can be read by JSONReader
            assert isinstance(read(buf), JSONReader)
            # send the bytes back to the client
            conn.sendall(buf.getvalue())
        conn.close()

    # start the server
    thread = threading.Thread(target=start_server)
    thread.start()
    time.sleep(1)

    # read the sample file into a BytesIO stream
    client_send_buf = BytesIO()
    with JSONWriter(client_send_buf) as json:
        json.set_root(read_sample('json_sample.json'))

    # send the bytes to the server
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(('localhost', port))
    client.sendall(client_send_buf.getvalue())
    client_send_buf.close()

    # get the bytes back from the server
    with BytesIO(client.recv(2**18)) as client_recv_buf:
        assert isinstance(read(client_recv_buf), JSONReader)

    # cleanup
    client.close()
    thread.join()
