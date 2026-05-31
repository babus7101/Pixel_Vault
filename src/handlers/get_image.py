"""Lambda handler — Get / download a single image.

GET /images/{image_id}

Returns a pre-signed S3 URL (valid for 1 hour) that the client can use to
download the actual image binary.  Metadata is also returned.
"""
import logging

from src.utils.aws_clients import get_s3_client, get_dynamodb_table, S3_BUCKET
from src.utils.response import success, error, sanitise_item

logger = logging.getLogger(__name__)

PRESIGNED_URL_EXPIRY = 3600  # seconds


def handler(event, context):
    """Return image metadata and a pre-signed download URL."""
    path_params = event.get("pathParameters") or {}
    image_id = path_params.get("image_id")

    if not image_id:
        return error("image_id path parameter is required")

    table = get_dynamodb_table()
    try:
        result = table.get_item(Key={"image_id": image_id})
    except Exception as exc:
        logger.error("DynamoDB get_item failed for %s: %s", image_id, exc)
        return error("Failed to retrieve image metadata", status_code=500)

    item = result.get("Item")
    if not item:
        return error("Image not found", status_code=404)

    # Generate pre-signed download URL
    s3 = get_s3_client()
    try:
        download_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": item["s3_key"]},
            ExpiresIn=PRESIGNED_URL_EXPIRY,
        )
    except Exception as exc:
        logger.error("Failed to generate presigned URL for %s: %s", image_id, exc)
        return error(f"Failed to generate download URL: {str(exc)}", status_code=500)

    clean_item = sanitise_item(item)
    clean_item["download_url"] = download_url

    return success({"image": clean_item})
