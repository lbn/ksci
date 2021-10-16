import celery
import kubernetes.client as klient

from kscipy import client
from kscipy.config import config
from kscipy.app import job

from . import services

NAMESPACE_JOBS = "jobs"

celery_app = celery.Celery("ksci", broker=config.rabbitmq.url, backend="rpc://")
ksci_client = client.KSCI(config.url)


class CeleryJobRun(services.JobRun):
    def start_logger(self, pod_name: str):
        log_writer.delay(self.job.json(), pod_name)


@celery_app.task
def run(job_data: str):
    job_run = CeleryJobRun(job.resources.RunJob.parse_raw(job_data))
    try:
        job_run.watch_pod_phase()
    except klient.ApiException as e:
        job.to_status(job.resources.RunJobStatus.failed)


@celery_app.task
def log_writer(job_data: str, pod_name: str):
    try:
        run_job = job.resources.RunJob.parse_raw(job_data)
        services.LogWriter(run_job, pod_name).stream()
    except Exception as err:
        print(err)
        raise
