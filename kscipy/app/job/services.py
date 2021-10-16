import typing as tp
import tempfile
import io
import abc

import kubernetes
import kubernetes.client as klient
import git
from kafka import KafkaProducer
from thrift.protocol import TBinaryProtocol
from thrift.transport import TTransport

from . import resources
from kscipy import client
from kscipy.config import config
from kscipy.data.job import ttypes as job_ttypes


kubernetes.config.load_incluster_config()
NAMESPACE_JOBS = "jobs"

_producer = None


def producer():
    global _producer
    if _producer is None:
        _producer = KafkaProducer(bootstrap_servers=config.kafka.hosts)
    return _producer


def _produce(topic: str, entity: object, key: tp.Union[str, bytes] = None):
    thrift_out = TTransport.TMemoryBuffer()
    protocol_out = TBinaryProtocol.TBinaryProtocol(thrift_out)
    entity.write(protocol_out)  # type: ignore
    data = thrift_out.getvalue()
    try:
        producer().send(topic, data, key=key)
    except Exception as err:
        print("err", err)
    producer().flush()


class LogWriter:
    def __init__(self, job: resources.RunJob, pod_name: str):
        self.job = job
        self.pod_name = pod_name

    def stream(self):
        core_v1 = klient.CoreV1Api()
        watch = kubernetes.watch.Watch()
        for line in watch.stream(
            core_v1.read_namespaced_pod_log,
            name=self.pod_name,
            namespace=NAMESPACE_JOBS,
        ):
            self._send_log(line)

    def _send_log(self, line: str):
        _produce(
            "logs",
            job_ttypes.LogWrite(
                job_id=self.job.id.bytes, log_id=self.job.log_id.bytes, line=line + "\n"
            ),
            key=self.job.id.bytes,
        )


class Job:
    def __init__(self, job: resources.RunJob):
        self.job = job

    def to_status(
        self, status: resources.RunJobStatus, message: tp.Optional[str] = None
    ):
        print("CHANGE JOB STATUS TO", status)
        _produce(
            "job_status",
            job_ttypes.JobStatusUpdate(
                job_id=self.job.id.bytes, status=status.value, message=message
            ),
        )


class JobRun:
    def __init__(self, job: resources.RunJob):
        self.ksci_client = client.KSCI(config.url)
        self.job = job
        self.job_svc = Job(job)
        self._clone_and_upload()
        batch_v1 = klient.BatchV1Api()
        batch_v1.create_namespaced_job(
            NAMESPACE_JOBS,
            self._create_job_object(),
        )

    @abc.abstractmethod
    def start_logger(self, pod_name: str):
        ...

    def watch_pod_phase(self) -> klient.V1Pod:
        core_v1 = klient.CoreV1Api()
        watch = kubernetes.watch.Watch()
        started_log = False
        termination_statuses = {
            resources.RunJobStatus.succeeded,
            resources.RunJobStatus.failed,
        }
        status = "pending"
        for event in watch.stream(
            func=core_v1.list_namespaced_pod,
            namespace=NAMESPACE_JOBS,
            label_selector=f"job-name={self._k8s_job_name}",
        ):
            try:
                new_status = event["object"].status.phase.lower()
                job_status = resources.RunJobStatus(new_status)
                if new_status != status:
                    self.job_svc.to_status(job_status)
                    status = new_status
                if not started_log and job_status in (
                    {resources.RunJobStatus.running} | termination_statuses
                ):
                    started_log = True
                    self.start_logger(event["object"].metadata.name)
                if job_status in termination_statuses:
                    watch.stop()
            except Exception as err:
                # TODO: use Kafka to do this
                print("Exception:")
                print(err)

    def _clone_and_upload(self):
        stream = io.BytesIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = git.Repo.clone_from(self.job.repo, tmpdir)
            repo.archive(stream, format="zip")
            stream.seek(0)
            self.ksci_client.object(self.job.repo_object_id).upload(stream.getvalue())

    def _upload_script(self, steps: tp.List[str]) -> client.KSCIObject:
        obj = self.ksci_client.object()
        obj.upload(("\n".join(steps)).encode())
        return obj

    @property
    def _k8s_job_name(self):
        return f"user-job-{str(self.job.id)}"

    def _create_job_object(self) -> klient.V1Job:
        volume_workdir = klient.V1Volume(
            name="workdir",
        )
        volume_output = klient.V1Volume(
            name="output",
        )
        volume_mount_workdir = klient.V1VolumeMount(
            name=volume_workdir.name, mount_path="/workdir"
        )
        volume_mount_output = klient.V1VolumeMount(
            name=volume_output.name, mount_path="/output"
        )

        cv_url = self.ksci_client.object(self.job.repo_object_id).url
        finaliser_path = "/workdir/.ksci-internal/ksci-finaliser"
        steps = self.job.steps.copy()
        steps.append(finaliser_path)
        steps_script_url = self._upload_script(steps).url
        steps_path = "/workdir/.ksci-internal/steps.sh"
        template = klient.V1PodTemplateSpec(
            metadata=klient.V1ObjectMeta(labels={"job_id": str(self.job.id)}),
            spec=klient.V1PodSpec(
                restart_policy="Never",
                containers=[
                    klient.V1Container(
                        name="steps",
                        image=self.job.image,
                        args=["/bin/bash", steps_path],
                        volume_mounts=[volume_mount_workdir, volume_mount_output],
                        working_dir=volume_mount_workdir.mount_path,
                        env=[
                            klient.V1EnvVar(
                                name="KSCI_OUTPUT_DIR",
                                value=volume_mount_output.mount_path,
                            ),
                            klient.V1EnvVar(
                                name="KSCI_OUTPUT_URL",
                                value=self.ksci_client.object(
                                    self.job.output_object_id
                                ).url,
                            ),
                        ],
                    )
                ],
                init_containers=[
                    klient.V1Container(
                        name="prepare",
                        image="larcher/ksci-prep:latest",
                        args=[
                            "/bin/sh",
                            "-c",
                            "; ".join(
                                [
                                    "mkdir /workdir/.ksci-internal",
                                    "cp /steps-binaries/* /workdir/.ksci-internal",
                                    f"wget {steps_script_url} -O {steps_path}",
                                    f"wget {cv_url} -O /tmp/cv.zip",
                                    "unzip /tmp/cv.zip -d /workdir",
                                ]
                            ),
                        ],
                        volume_mounts=[volume_mount_workdir],
                        working_dir=volume_mount_workdir.mount_path,
                    )
                ],
                volumes=[volume_workdir, volume_output],
            ),
        )
        spec = klient.V1JobSpec(
            template=template, backoff_limit=3, ttl_seconds_after_finished=60
        )
        job = klient.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=klient.V1ObjectMeta(name=self._k8s_job_name),
            spec=spec,
        )
        return job
