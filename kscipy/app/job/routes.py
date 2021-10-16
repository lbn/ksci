import typing as tp
import uuid

from flask import Blueprint, url_for
from flask_pydantic import validate
import pydantic
import urllib.parse


from . import resources
from . import tasks
from kscipy.config import config

app = Blueprint("job", __name__)


class SubmitRequest(pydantic.BaseModel):
    image: str
    repo: str
    steps: tp.List[str]


class SubmitResponse(pydantic.BaseModel):
    job: resources.RunJob
    log: str
    output: str


class StatusUpdateRequest(pydantic.BaseModel):
    status: resources.RunJobStatus
    message: tp.Optional[str]


@app.route("/api/job/submit", methods=["POST"])
@validate()
def job_submit(body: SubmitRequest):
    job_resource = resources.RunJob.create(
        image=body.image, repo=body.repo, steps=body.steps
    )
    tasks.run.delay(job_resource.json())
    return SubmitResponse(
        job=job_resource,
        log=urllib.parse.urljoin(
            config.url, url_for("object_download", object_id=str(job_resource.log_id))
        ),
        output=urllib.parse.urljoin(
            config.url,
            url_for("object_download", object_id=str(job_resource.output_object_id)),
        ),
    )


@app.route("/api/job/<job_id>", methods=["GET"])
@validate()
def job(job_id: str) -> tp.Optional[resources.RunJob]:
    return resources.RunJob.load(uuid.UUID(job_id))


@app.route("/api/job/<job_id>/status", methods=["GET"])
@validate()
def job_status(job_id: str) -> resources.RunJobStatusTransition:
    return resources.RunJobStatusTransition.last_for_job_id(uuid.UUID(job_id))


@app.route("/api/job/<job_id>/status", methods=["PATCH"])
@validate()
def job_status_update(job_id: uuid.UUID, body: StatusUpdateRequest):
    resources.RunJobStatusTransition.update_for_job_id(
        job_id, body.status, body.message
    )
    return "", 201
