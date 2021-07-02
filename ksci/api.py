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

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(
    app,
    origins=[
        "http://localhost:3000",
        config.url,
    ],
)


class SubmitRequest(pydantic.BaseModel):
    image: str
    repo: str
    steps: tp.List[str]


class SubmitResponse(pydantic.BaseModel):
    job: db.RunJob
    log: str
    output: str


@app.route("/api/job/submit", methods=["POST"])
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
            config.url, url_for("object_download", object_id=job.object_id_logs)
        ),
        output=urllib.parse.urljoin(
            config.url, url_for("object_download", object_id=job.object_id_output)
        ),
    )


@app.route("/api/job/<job_id>", methods=["GET"])
@validate()
def job(job_id: str) -> db.RunJob:
    return db.RunJob.load(job_id)


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
