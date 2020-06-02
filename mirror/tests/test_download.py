from mirror import download
import requests.sessions


def monkeypatch(obj, key, value):
    original_value = getattr(obj, key)
    setattr(obj, key, value)
    try:
        yield
    finally:
        setattr(obj, key, original_value)


class MockSession(requests.sessions.Session):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.mount()


def test_in_memory