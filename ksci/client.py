import typing as tp
import uuid
import urllib.parse
import json

import requests

from ksci import resources
from ksci import api


class KSCIObject:
    def __init__(self, client: "KSCI", object_id: tp.Optional[uuid.UUID] = None):
        self._object_id = object_id if object_id else uuid.uuid4()
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


class KSCILog:
    def __init__(self, client: "KSCI", log_id: tp.Optional[uuid.UUID] = None):
        self._log_id = log_id if log_id else uuid.uuid4()
        self._client = client

    @property
    def path(self):
        return f"log/{self._log_id}"

    @property
    def url(self):
        return self._client.url_for(self.path)

    def append(self, data: bytes):
        self._client.do("PATCH", self.path, data=data)


class KSCIJob:
    def __init__(self, client: "KSCI", job_id: uuid.UUID):
        self._job_id = job_id
        self._client = client

    def to_status(
        self, status: resources.RunJobStatus, message: tp.Optional[str] = None
    ):
        self._client.do(
            "PATCH",
            f"job/{self._job_id}/status",
            json=json.loads(
                api.StatusUpdateRequest(status=status, message=message).json()
            ),
        )


class KSCI:
    def __init__(self, base_url: str):
        self._base_url = base_url

    def object(self, object_id: tp.Optional[uuid.UUID] = None):
        return KSCIObject(self, object_id)

    def job(self, job_id: uuid.UUID):
        return KSCIJob(self, job_id)

    def log(self, log_id: tp.Optional[uuid.UUID] = None):
        return KSCILog(self, log_id)

    def url_for(self, path: str) -> str:
        return urllib.parse.urljoin(self._base_url, f"api/{path}")

    def do(self, method: str, path: str, *args, **kwargs):
        return requests.request(method, self.url_for(path), *args, **kwargs)
