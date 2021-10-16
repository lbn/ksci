import typing as tp
import uuid

from flask import Flask, request, Response
from flask_cors import CORS

from kscipy import db
from kscipy.config import config
from kscipy.app import job

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(
    app,
    origins=[
        "http://localhost:3000",
        config.url,
    ],
)


app.register_blueprint(job.routes.app)


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
