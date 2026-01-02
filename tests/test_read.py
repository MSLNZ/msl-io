import socket
import threading
import time
from importlib.util import find_spec
from io import BytesIO
from pathlib import Path

import pytest

from msl.io import JSONWriter, read
from msl.io.readers import JSONReader

samples = Path(__file__).parent / "samples"


def test_raises() -> None:
    # file does not exist
    with pytest.raises(OSError, match=r"No such file"):
        _ = read("does_not.exist")

    # unicode filename
    with pytest.raises(OSError, match=r"No such file"):
        _ = read("Filé döes ñot éxist")  # cSpell: ignore Filé döes ñot éxist

    # no Reader class exists to read this test_read.py file
    with pytest.raises(OSError, match=r"No Reader exists"):
        _ = read(__file__)

    # unicode filename
    with pytest.raises(OSError, match=r"No Reader exists"):
        _ = read(samples / "uñicödé")  # cSpell: ignore uñicödé


@pytest.mark.skipif(find_spec("h5py") is None, reason="h5py is not installed")
def test_unicode_filename() -> None:
    root = read(samples / "uñicödé.h5")
    assert root.metadata.is_unicode
    assert isinstance(root.file, str)
    assert root.file.endswith("uñicödé.h5")
    assert "café" in root
    assert "/café" in root
    assert "café/caña" in root  # cSpell: ignore caña
    assert "/café/caña" in root
    assert "caña" in root["café"]
    assert "/caña" in root["/café"]
    assert "cafécaña" not in root  # cSpell: ignore cafécaña


def test_socket() -> None:
    # test that we can read/write a Root object from a socket stream

    # get any available port
    sock = socket.socket()
    sock.bind(("", 0))
    port = sock.getsockname()[1]
    sock.close()

    # the server will run in a separate thread
    def start_server() -> None:
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
        root_client = read(samples / "json_sample.json")
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

    assert root_client == root_server

    # cleanup
    client.close()
    thread.join()


def test_pathlib() -> None:
    root1 = read(samples / "json_sample.json")
    assert isinstance(root1.file, str)
    root2 = read(Path(root1.file))
    assert root1 == root2
