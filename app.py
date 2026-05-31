"""Lightweight Flask server to expose Lambda handlers as HTTP endpoints.

Usage:
    python app.py

Requires LocalStack running (docker-compose up -d && ./setup_localstack.sh).
"""
import json
import os

from flask import Flask, request, jsonify

os.environ.setdefault("LOCALSTACK_ENDPOINT", "http://localhost:4566")
os.environ.setdefault("S3_BUCKET", "pixelvault-images")
os.environ.setdefault("DYNAMODB_TABLE", "pixelvault-images")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

from src.handlers.upload import handler as upload_handler
from src.handlers.list_images import handler as list_handler
from src.handlers.get_image import handler as get_handler
from src.handlers.delete_image import handler as delete_handler

app = Flask(__name__)


def _to_flask(lambda_response):
    body = json.loads(lambda_response.get("body", "{}"))
    status = lambda_response.get("statusCode", 500)
    return jsonify(body), status


@app.route("/images", methods=["POST"])
def upload():
    event = {"body": json.dumps(request.get_json(force=True))}
    return _to_flask(upload_handler(event, None))


@app.route("/images", methods=["GET"])
def list_images():
    event = {"queryStringParameters": dict(request.args) or None}
    return _to_flask(list_handler(event, None))


@app.route("/images/<image_id>", methods=["GET"])
def get_image(image_id):
    event = {"pathParameters": {"image_id": image_id}}
    return _to_flask(get_handler(event, None))


@app.route("/images/<image_id>", methods=["DELETE"])
def delete_image(image_id):
    event = {"pathParameters": {"image_id": image_id}}
    return _to_flask(delete_handler(event, None))


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print("\n  PixelVault API running at http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=debug)
