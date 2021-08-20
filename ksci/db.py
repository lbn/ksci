import typing as tp
import uuid
import enum
import json

import redis
import pydantic
import cassandra.cluster

from ksci.config import config


rclient = redis.from_url(config.redis.url)
cclient = cassandra.cluster.Cluster(config.cassandra.hosts.split()).connect("ksci")


class NotFoundError(Exception):
    pass


def new_id() -> str:
    return str(uuid.uuid4())


class RunJobStatus(enum.Enum):
    pending = "pending"
    unknown = "unknown"
    running = "running"
    succeeded = "succeeded"
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

    class Config:
        use_enum_values = True

    @staticmethod
    def _key(job_id: str):
        return f"job:{job_id}"

    def update(self, field: str, value: tp.Any):
        rclient.hset(self._key(self.job_id), field, json.dumps(value))

    def save(self):
        for key, value in json.loads(self.json()).items():
            self.update(key, value)

    @classmethod
    def load(cls, job_id: str) -> "RunJob":
        if not rclient.exists(cls._key(job_id)):
            raise NotFoundError()
        return cls(
            **{
                key.decode(): json.loads(value)
                for key, value in rclient.hgetall(cls._key(job_id)).items()
            }
        )

    def to_status(self, status: RunJobStatus):
        self.status = status
        self.update("status", status.value)


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


class Log:
    def __init__(self, log_id: str):
        self._key = uuid.UUID(log_id)

    def append(self, data: bytes):
        cclient.execute(
            "INSERT INTO logs (id, time, log) VALUES (%s, now(), %s)",
            (self._key, data.decode()),
        )

    def download(self, after_id: tp.Optional[str] = None) -> tp.Tuple[bytes, str]:
        """
        Get logs after `after_id` (time UUID).

        :return: log contents and last line UUID
        """

        if after_id:
            rows = cclient.execute(
                "select time, log from logs where id = %s and time > %s",
                (self._key, uuid.UUID(after_id)),
            ).current_rows
        else:
            rows = cclient.execute(
                "select time, log from logs where id = %s", (self._key,)
            ).current_rows
        if not rows:
            raise NotFoundError()
        return b"".join(row.log.encode() for row in rows), str(rows[-1].time)
