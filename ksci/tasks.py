import os
import typing as tp
import tempfile
import io

import celery
import kubernetes
import kubernetes.client as klient
import git

from ksci import client
from ksci import db
from ksci.config import config

NAMESPACE_JOBS = "jobs"

print("CELERY", config.rabbitmq.url)
celery_app = celery.Celery("ksci", broker=config.rabbitmq.url, backend="rpc://")
ksci_client = client.KSCI(config.url)

kubernetes.config.load_incluster_config()


def k8s_job_name(job: db.RunJob):
    return f"user-job-{job.job_id}"


def upload_script(steps: tp.List[str]) -> client.KSCIObject:
    obj = ksci_client.object()
    obj.upload(("\n".join(steps)).encode())
    return obj


def create_job_object(job: db.RunJob) -> klient.V1Job:
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

    cv_url = ksci_client.object(job.object_id_cv).url
    finaliser_path = "/workdir/.ksci-internal/ksci-finaliser"
    steps = job.steps.copy()
    steps.append(finaliser_path)
    steps_script_url = upload_script(steps).url
    steps_path = "/workdir/.ksci-internal/steps.sh"
    template = klient.V1PodTemplateSpec(
        metadata=klient.V1ObjectMeta(labels={"job_id": job.job_id}),
        spec=klient.V1PodSpec(
            restart_policy="Never",
            containers=[
                klient.V1Container(
                    name="steps",
                    image=job.image,
                    args=["/bin/bash", steps_path],
                    volume_mounts=[volume_mount_workdir, volume_mount_output],
                    working_dir=volume_mount_workdir.mount_path,
                    env=[
                        klient.V1EnvVar(
                            name="KSCI_OUTPUT_DIR", value=volume_mount_output.mount_path
                        ),
                        klient.V1EnvVar(
                            name="KSCI_OUTPUT_URL",
                            value=ksci_client.object(job.object_id_output).url,
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
        metadata=klient.V1ObjectMeta(name=k8s_job_name(job)),
        spec=spec,
    )
    return job


def watch_pod_phase(job: db.RunJob) -> klient.V1Pod:
    core_v1 = klient.CoreV1Api()
    watch = kubernetes.watch.Watch()
    started_log = False
    termination_statuses = {db.RunJobStatus.succeeded, db.RunJobStatus.failed}
    for event in watch.stream(
        func=core_v1.list_namespaced_pod,
        namespace=NAMESPACE_JOBS,
        label_selector=f"job-name={k8s_job_name(job)}",
    ):
        job_status = db.RunJobStatus(event["object"].status.phase.lower())
        if job_status != job.status:
            job.to_status(job_status)
        if not started_log and job_status in (
            {db.RunJobStatus.running} | termination_statuses
        ):
            started_log = True
            log_writer.delay(job.dict(), event["object"].metadata.name)
        if job_status in termination_statuses:
            watch.stop()


def create_job(job: db.RunJob):
    batch_v1 = klient.BatchV1Api()
    batch_v1.create_namespaced_job(
        NAMESPACE_JOBS,
        create_job_object(job),
    )


def clone_and_upload(job: db.RunJob):
    stream = io.BytesIO()
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = git.Repo.clone_from(job.repo, tmpdir)
        repo.archive(stream, format="zip")
        stream.seek(0)
        ksci_client.object(job.object_id_cv).upload(stream.getvalue())


@celery_app.task
def run(job_data: dict):
    job = db.RunJob(**job_data)
    clone_and_upload(job)
    try:
        create_job(job)
        watch_pod_phase(job)
    except klient.ApiException as e:
        job.to_status(db.RunJobStatus.failed)


@celery_app.task
def log_writer(job_data: dict, pod_name: str):
    job = db.RunJob(**job_data)
    kscii_object = ksci_client.object(job.object_id_logs)
    core_v1 = klient.CoreV1Api()
    watch = kubernetes.watch.Watch()
    for line in watch.stream(
        core_v1.read_namespaced_pod_log,
        name=pod_name,
        namespace=NAMESPACE_JOBS,
    ):
        kscii_object.append((line + "\n").encode())
