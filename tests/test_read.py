import pathlib
import socket
import threading
import time
from io import BytesIO

import pytest

try:
    import h5py
except ImportError:
    h5py = None

from tests.helper import read_sample
from tests.helper import roots_equal
from msl.io import JSONWriter
from msl.io import read
from msl.io.readers import JSONReader


def test_raises():
    # file does not exist
    with pytest.raises(OSError, match=r"No such file"):
        read("does_not.exist")

    # unicode filename
    with pytest.raises(OSError, match=r"No such file"):
        read("Filé döes ñot éxist")

    # no Reader class exists to read this test_read.py file
    with pytest.raises(OSError, match=r"No Reader exists"):
        read(__file__)

    # unicode filename
    with pytest.raises(OSError, match=r"No Reader exists"):
        read_sample("uñicödé")


@pytest.mark.skipif(h5py is None, reason="h5py is not installed")
def test_unicode_filename():
    root = read_sample("uñicödé.h5")
    assert root.metadata.is_unicode
    assert root.file.endswith("uñicödé.h5")
    assert "café" in root
    assert "/café" in root
    assert "café/caña" in root
    assert "/café/caña" in root
    assert "caña" in root["café"]
    assert "/caña" in root["/café"]
    assert "cafécaña" not in root


def test_socket():
    # test that we can read/write a Root object from a socket stream

    # get any available port
    sock = socket.socket()
    sock.bind(("", 0))
    port = sock.getsockname()[1]
    sock.close()

    # the server will run in a separate thread
    def start_server():
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("localhost", port))
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
        root_client = read_sample("json_sample.json")
        json.set_root(root_client)

    # send the bytes to the server
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("localhost", port))
    client.sendall(client_send_buf.getvalue())
    client_send_buf.close()

    # get the bytes back from the server
    with BytesIO(client.recv(2**18)) as client_recv_buf:
        root_server = read(client_recv_buf)
        assert isinstance(root_server, JSONReader)

    assert roots_equal(root_client, root_server)

    # cleanup
    client.close()
    thread.join()


def test_pathlib():
    root1 = read_sample("json_sample.json")
    root2 = read(pathlib.Path(root1.file))
    assert roots_equal(root1, root2)
