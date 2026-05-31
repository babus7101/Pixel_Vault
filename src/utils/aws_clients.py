"""AWS service clients with LocalStack support."""
import os
import boto3


def _endpoint_url():
    """Return LocalStack endpoint if LOCALSTACK_ENDPOINT is set."""
    return os.environ.get("LOCALSTACK_ENDPOINT")


def get_s3_client():
    return boto3.client("s3", endpoint_url=_endpoint_url())


def get_dynamodb_resource():
    return boto3.resource("dynamodb", endpoint_url=_endpoint_url())


def get_dynamodb_table(table_name=None):
    table_name = table_name or os.environ.get("DYNAMODB_TABLE", "pixelvault-images")
    return get_dynamodb_resource().Table(table_name)


S3_BUCKET = os.environ.get("S3_BUCKET", "pixelvault-images")
S3_BUCKET = os.environ.get("S3_BUCKET", "pixelvault-images")
