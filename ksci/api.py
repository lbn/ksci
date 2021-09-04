import typing as tp
import uuid
import urllib.parse

from flask import Flask, request, Response, url_for
from flask_pydantic import validate
import pydantic
from flask_cors import CORS

from ksci import tasks
from ksci import db
from ksci.config import config
from ksci import resources

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(
    app, origins=["http://localhost:3000", config.url,],
)


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


@app.route("/api/object", methods=["POST"])
def object_create():
    return str(uuid.uuid4())


@app.route("/api/object/<object_id>", methods=["PUT"])
def object_upload(object_id):
    db.Object(object_id).upload(request.get_data())
    return "", 201


@app.route("/api/object/<object_id>", methods=["PATCH"])
def object_append(object_id):
    db.Object(object_id).append(request.get_data())
    return "", 201


@app.route("/api/log/<log_id>", methods=["PATCH"])
def log_append(log_id):
    db.Log(log_id).append(request.get_data())
    return "", 201


@app.route("/api/log/<log_id>", methods=["GET"])
def log_download(log_id):
    try:
        data, last_log_id = db.Log(log_id).download(request.args.get("after-id"))
    except db.NotFoundError:
        return "", 200
    return Response(data, headers={"Last-Log-Id": last_log_id}, mimetype="text/plain")


@app.route("/api/object/<object_id>", methods=["GET"])
def object_download(object_id):
    try:
        data = db.Object(object_id).download()
        if request.args.get("output") is not None:
            return Response(
                data,
                mimetype="application/zip",
                headers={
                    "Content-disposition": f"attachment; filename=output-{object_id}.zip"
                },
            )
        return Response(data, mimetype="application/octet-stream")
    except db.NotFoundError:
        return "", 404


@app.errorhandler(404)
def page_not_found(e):
    return app.send_static_file("index.html")
