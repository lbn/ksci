import os
import typing as tp
import tempfile
import json
import io

import celery
import kubernetes
import kubernetes.client as klient
import git

from ksci import client
from ksci import db

NAMESPACE_JOBS = "jobs"

celery_app = celery.Celery("ksci", broker=os.getenv("CELERY_URL"), backend="rpc://")
ksci_client = client.KSCI(os.getenv("KSCI_URL"))

kubernetes.config.load_kube_config()


def upload_script(steps: tp.List[str]) -> client.KSCIObject:
    obj = ksci_client.object()
    obj.upload(("\n".join(steps)).encode())
    return obj


def create_job_object(job_name: str, job: db.RunJob) -> klient.V1Job:
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
    finaliser_url = "http://sw1.archer.onl/download/ksci-finaliser"
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
                    image="alpine:latest",
                    args=[
                        "/bin/sh",
                        "-c",
                        "; ".join(
                            [
                                "mkdir /workdir/.ksci-internal",
                                f"wget {finaliser_url} -O {finaliser_path}",
                                f"wget {steps_script_url} -O {steps_path}",
                                f"wget {cv_url} -O /tmp/cv.zip",
                                f"chmod +x {finaliser_path}",
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
        metadata=klient.V1ObjectMeta(name=job_name),
        spec=spec,
    )
    return job


def get_ready_job_pod(job_name: str) -> klient.V1Pod:
    core_v1 = klient.CoreV1Api()
    watch = kubernetes.watch.Watch()
    for event in watch.stream(
        func=core_v1.list_namespaced_pod,
        namespace=NAMESPACE_JOBS,
        label_selector=f"job-name={job_name}",
    ):
        if event["object"].status.phase in ("Running", "Succeeded"):
            watch.stop()
            return event["object"]


def write_logs(pod: klient.V1Pod, kscii_object: client.KSCIObject):
    core_v1 = klient.CoreV1Api()
    watch = kubernetes.watch.Watch()
    for line in watch.stream(
        core_v1.read_namespaced_pod_log,
        name=pod.metadata.name,
        namespace=NAMESPACE_JOBS,
    ):
        kscii_object.append((line + "\n").encode())


def create_job(job_name: str, job: db.RunJob):
    batch_v1 = klient.BatchV1Api()
    batch_v1.create_namespaced_job(
        NAMESPACE_JOBS,
        create_job_object(job_name, job),
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
    job_name = f"user-job-{job.job_id}"
    clone_and_upload(job)
    try:
        create_job(job_name, job)
        job.to_status(db.RunJobStatus.created)
        pod = get_ready_job_pod(job_name)
        job.to_status(db.RunJobStatus.running)
        write_logs(pod, ksci_client.object(job.object_id_logs))

        batch_v1 = klient.BatchV1Api()
        resp = batch_v1.read_namespaced_job_status(job_name, NAMESPACE_JOBS)
        open("jobstatus_bad.json", "w").write(
            json.dumps(klient.ApiClient().sanitize_for_serialization(resp))
        )

    except klient.ApiException as e:
        print("EXCEPTION", e)
    return None
