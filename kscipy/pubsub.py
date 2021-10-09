import typing as tp

from thrift.protocol import TBinaryProtocol
from thrift.transport import TTransport

from kscipy import resources
from kscipy.data.job import ttypes as job_ttypes


def produce(producer, topic: str, entity: object, key: tp.Union[str, bytes]) -> bytes:
    thrift_out = TTransport.TMemoryBuffer()
    protocol_out = TBinaryProtocol.TBinaryProtocol(thrift_out)
    entity.write(protocol_out)
    data = thrift_out.getvalue()
    try:
        producer.send(topic, data, key=key)
    except Exception as err:
        print("err", err)
    producer.flush()


def send_log(producer, job: resources.RunJob, line: str):
    produce(
        producer,
        "logs",
        job_ttypes.LogWrite(
            job_id=job.id.bytes, log_id=job.log_id.bytes, line=line + "\n"
        ),
        key=job.id.bytes,
    )
