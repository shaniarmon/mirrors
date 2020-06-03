from mirror import download
import requests.sessions
import requests_mock
import contextlib
import io


@contextlib.contextmanager
def monkeypatch(obj, key, value):
    original_value = getattr(obj, key)
    setattr(obj, key, value)
    try:
        yield
    finally:
        setattr(obj, key, original_value)


class MockSession(requests.sessions.Session):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        mock_adapter = requests_mock.Adapter()
        self.mount("mock://", mock_adapter)
        mock_adapter.register_uri('GET', 'mock://test.com', text='data')


def test_download_in_memory():
    buf = io.BytesIO()
    with monkeypatch(requests.sessions, "Session", MockSession):
        download.download_file("mock://test.com", buf)

    assert buf.getvalue() == b'data'
