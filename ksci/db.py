import os
import typing as tp
import uuid
import enum

import redis
import pydantic


rclient = redis.from_url(os.getenv("REDIS_URL"))


class NotFoundError(Exception):
    pass


def new_id() -> str:
    return str(uuid.uuid4())


class RunJobStatus(enum.Enum):
    pending = "pending"
    created = "created"
    running = "running"
    completed = "completed"
    failed = "failed"


class RunJob(pydantic.BaseModel):
    job_id: str = pydantic.Field(default_factory=new_id)
    image: str
    steps: tp.List[str]
    object_id_logs: str = pydantic.Field(default_factory=new_id)
    object_id_output: str = pydantic.Field(default_factory=new_id)
    repo: str
    object_id_cv: str = pydantic.Field(default_factory=new_id)
    status: str = RunJobStatus.pending

    @staticmethod
    def _key(job_id: str):
        return f"job:{job_id}"

    def save(self):
        rclient.set(self._key(self.job_id), self.json())

    @classmethod
    def load(cls, job_id: str) -> "RunJob":
        return cls.parse_raw(rclient.get(cls._key(job_id)))

    def to_status(self, status: RunJobStatus):
        self.status = status
        self.save()


class Object:
    def __init__(self, object_id: str):
        self._key = f"object:{object_id}"

    def append(self, data: bytes):
        rclient.rpush(self._key, data)

    def upload(self, data: bytes):
        rclient.set(self._key, data)

    def download(self) -> bytes:
        if not rclient.exists(self._key):
            raise NotFoundError()
        if rclient.type(self._key).decode() == "list":
            return b"".join(rclient.lrange(self._key, 0, -1))
        return rclient.get(self._key)
