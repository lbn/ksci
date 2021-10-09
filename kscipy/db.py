import typing as tp
import uuid
import enum

import redis
import cassandra.cluster
from cassandra.cqlengine import connection
from cassandra.cqlengine.models import Model
from cassandra.cqlengine import columns
from cassandra import auth

from kscipy.config import config

KEYSPACE = "ksci"

rclient = redis.from_url(config.redis.url)
auth_provider = auth.PlainTextAuthProvider(
    username=config.cassandra.username, password=config.cassandra.password
)
cclient = cassandra.cluster.Cluster(
    config.cassandra.hosts.split(), auth_provider=auth_provider
).connect(KEYSPACE)
connection.setup(config.cassandra.hosts.split(), KEYSPACE, auth_provider=auth_provider)


class NotFoundError(Exception):
    pass


class RunJobStatusTransition(Model):
    __keyspace__ = KEYSPACE
    job_id = columns.TimeUUID(primary_key=True)
    id = columns.TimeUUID(primary_key=True, default=uuid.uuid1, clustering_order="DESC")
    status = columns.Text()
    message = columns.Text()


class RunJob(Model):
    __keyspace__ = KEYSPACE
    id = columns.TimeUUID(primary_key=True, default=uuid.uuid1)
    image = columns.Text()
    repo = columns.Text()
    log_id = columns.UUID(default=uuid.uuid4)
    output_object_id = columns.UUID(default=uuid.uuid4)
    repo_object_id = columns.UUID(default=uuid.uuid4)
    steps = columns.List(columns.Text)


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
