import typing as tp
import uuid
import urllib.parse

import requests


class KSCIObject:
    def __init__(self, client: "KSCI", object_id: tp.Optional[str] = None):
        self._object_id = object_id if object_id else str(uuid.uuid4())
        self._client = client

    @property
    def path(self):
        return f"object/{self._object_id}"

    @property
    def url(self):
        return self._client.url_for(self.path)

    def append(self, data: bytes):
        self._client.do("PATCH", self.path, data=data)

    def upload(self, data: bytes):
        self._client.do("PUT", self.path, data=data)


class KSCI:
    def __init__(self, base_url: str):
        self._base_url = base_url

    def object(self, object_id: tp.Optional[str] = None):
        return KSCIObject(self, object_id)

    def url_for(self, path: str) -> str:
        return urllib.parse.urljoin(self._base_url, f"api/{path}")

    def do(self, method: str, path: str, *args, **kwargs):
        return requests.request(method, self.url_for(path), *args, **kwargs)
