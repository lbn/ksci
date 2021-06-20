import os
import typing as tp
import uuid
import urllib.parse

from flask import Flask, request, Response, redirect, url_for
from flask_pydantic import validate
import pydantic

from ksci import tasks
from ksci import db

app = Flask(__name__)


ksci_url = os.getenv("KSCI_URL")


class SubmitRequest(pydantic.BaseModel):
    image: str
    repo: str
    steps: tp.List[str]


class SubmitResponse(pydantic.BaseModel):
    job: db.RunJob
    log: str
    output: str


@app.route("/")
def index():
    return "ksci"


@app.route("/job/submit", methods=["POST"])
@validate()
def job_submit(body: SubmitRequest):
    job = db.RunJob(
        image=body.image,
        repo=body.repo,
        steps=body.steps,
    )
    job.save()
    tasks.run.delay(job.dict())
    return SubmitResponse(
        job=job,
        log=urllib.parse.urljoin(
            ksci_url, url_for("object_download", object_id=job.object_id_logs)
        ),
        output=urllib.parse.urljoin(
            ksci_url, url_for("object_download", object_id=job.object_id_output)
        ),
    )


@app.route("/job/<job_id>", methods=["GET"])
@validate()
def job(job_id: str) -> db.RunJob:
    return db.RunJob.load(job_id)


@app.route("/object", methods=["POST"])
def object_create():
    return str(uuid.uuid4())


@app.route("/object/<object_id>", methods=["PUT"])
def object_upload(object_id):
    db.Object(object_id).upload(request.get_data())
    return "", 201


@app.route("/object/<object_id>", methods=["PATCH"])
def object_append(object_id):
    db.Object(object_id).append(request.get_data())
    return "", 201


@app.route("/object/<object_id>", methods=["GET"])
def object_download(object_id):
    try:
        data = db.Object(object_id).download()
        return Response(data, mimetype="application/octet-stream")
    except db.NotFoundError:
        return "", 404
