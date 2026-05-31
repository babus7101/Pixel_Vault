"""Lambda handler — Upload image with metadata.

POST /images
Body (JSON):
  {
    "user_id": "user123",
    "filename": "sunset.jpg",
    "content_type": "image/jpeg",
    "description": "A beautiful sunset",
    "tags": ["nature", "sunset"],
    "image_data": "<base64-encoded image>"
  }
"""
import base64
import binascii
import json
import logging
import os
import uuid
from datetime import datetime, timezone

from src.utils.aws_clients import get_s3_client, get_dynamodb_table, S3_BUCKET
from src.utils.response import success, error

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_FILENAME_LENGTH = 255
MAX_DESCRIPTION_LENGTH = 1000
MAX_TAGS = 20
MAX_TAG_LENGTH = 50


def _sanitise_filename(filename):
    """Strip directory components and traversal patterns to prevent path traversal."""
    name = os.path.basename(filename)
    # Reject filenames that are only dots (e.g. "..", ".")
    if name.strip(".") == "":
        return ""
    return name


def handler(event, context):
    """Upload an image to S3 and persist metadata in DynamoDB."""
    try:
        body = json.loads(event.get("body", "{}"))
    except (json.JSONDecodeError, TypeError):
        return error("Invalid JSON body")

    # --- Validate required fields ---
    user_id = body.get("user_id")
    filename = body.get("filename")
    content_type = body.get("content_type", "image/jpeg")
    image_data_b64 = body.get("image_data")

    if not user_id or not isinstance(user_id, str):
        return error("user_id is required")
    if not filename or not isinstance(filename, str):
        return error("filename is required")
    if not image_data_b64 or not isinstance(image_data_b64, str):
        return error("image_data is required")
    if content_type not in ALLOWED_CONTENT_TYPES:
        return error(f"Unsupported content_type. Allowed: {sorted(ALLOWED_CONTENT_TYPES)}")

    # Sanitise filename to prevent path traversal
    filename = _sanitise_filename(filename)
    if not filename:
        return error("filename is required")
    if len(filename) > MAX_FILENAME_LENGTH:
        return error(f"filename exceeds maximum length of {MAX_FILENAME_LENGTH}")

    # Validate description length
    description = body.get("description", "")
    if not isinstance(description, str):
        description = str(description)
    if len(description) > MAX_DESCRIPTION_LENGTH:
        return error(f"description exceeds maximum length of {MAX_DESCRIPTION_LENGTH}")

    # Validate tags
    tags = body.get("tags", [])
    if not isinstance(tags, list):
        return error("tags must be a list")
    if len(tags) > MAX_TAGS:
        return error(f"Maximum {MAX_TAGS} tags allowed")
    for tag in tags:
        if not isinstance(tag, str) or len(tag) > MAX_TAG_LENGTH:
            return error(f"Each tag must be a string of at most {MAX_TAG_LENGTH} characters")

    # --- Decode image ---
    try:
        image_bytes = base64.b64decode(image_data_b64, validate=True)
    except (binascii.Error, ValueError):
        return error("image_data must be valid base64")

    if len(image_bytes) > MAX_FILE_SIZE:
        return error(f"Image exceeds maximum size of {MAX_FILE_SIZE // (1024*1024)} MB")
    if len(image_bytes) == 0:
        return error("image_data must not be empty")

    # --- Generate identifiers ---
    image_id = str(uuid.uuid4())
    upload_date = datetime.now(timezone.utc).isoformat()
    s3_key = f"{user_id}/{image_id}/{filename}"

    # --- Upload to S3 ---
    s3 = get_s3_client()
    try:
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=image_bytes,
            ContentType=content_type,
        )
    except Exception as exc:
        logger.error("S3 upload failed for key %s: %s", s3_key, exc)
        return error("Failed to upload image to storage", status_code=500)

    # --- Save metadata to DynamoDB ---
    table = get_dynamodb_table()
    item = {
        "image_id": image_id,
        "user_id": user_id,
        "filename": filename,
        "content_type": content_type,
        "description": description,
        "tags": tags,
        "s3_key": s3_key,
        "upload_date": upload_date,
        "file_size": len(image_bytes),
    }
    try:
        table.put_item(Item=item)
    except Exception as exc:
        logger.error("DynamoDB put_item failed for %s: %s", image_id, exc)
        # Best-effort cleanup: remove the orphaned S3 object
        try:
            s3.delete_object(Bucket=S3_BUCKET, Key=s3_key)
        except Exception:
            logger.error("Failed to cleanup S3 object %s after DynamoDB failure", s3_key)
        return error("Failed to save image metadata", status_code=500)

    return success({"message": "Image uploaded successfully", "image": item}, status_code=201)
