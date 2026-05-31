"""Lambda handler — Delete an image.

DELETE /images/{image_id}

Removes the image from S3 and its metadata from DynamoDB.
"""
import logging

from src.utils.aws_clients import get_s3_client, get_dynamodb_table, S3_BUCKET
from src.utils.response import success, error

logger = logging.getLogger(__name__)


def handler(event, context):
    """Delete an image from S3 and its metadata from DynamoDB."""
    path_params = event.get("pathParameters") or {}
    image_id = path_params.get("image_id")

    if not image_id:
        return error("image_id path parameter is required")

    table = get_dynamodb_table()

    # Fetch metadata first to get the S3 key
    try:
        result = table.get_item(Key={"image_id": image_id})
    except Exception as exc:
        logger.error("DynamoDB get_item failed for %s: %s", image_id, exc)
        return error("Failed to retrieve image metadata", status_code=500)

    item = result.get("Item")
    if not item:
        return error("Image not found", status_code=404)

    s3_key = item["s3_key"]

    # Delete metadata from DynamoDB first (easier to retry S3 deletion)
    try:
        table.delete_item(Key={"image_id": image_id})
    except Exception as exc:
        logger.error("DynamoDB delete_item failed for %s: %s", image_id, exc)
        return error(f"Failed to delete image metadata: {str(exc)}", status_code=500)

    # Delete from S3
    s3 = get_s3_client()
    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=s3_key)
    except Exception as exc:
        logger.error("S3 delete failed for %s (metadata already removed): %s", s3_key, exc)
        return error(f"Failed to delete image from storage: {str(exc)}", status_code=500)

    return success({"message": "Image deleted successfully", "image_id": image_id})
