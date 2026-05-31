"""Shared pytest fixtures for PixelVault unit tests.

Uses moto to mock AWS services (S3 and DynamoDB) so tests run without
any external dependencies.
"""
import base64
import json
import os

import boto3
import pytest
from moto import mock_aws

# Point handlers at mocked services (no LocalStack endpoint needed in tests)
os.environ["S3_BUCKET"] = "pixelvault-images"
os.environ["DYNAMODB_TABLE"] = "pixelvault-images"
os.environ.pop("LOCALSTACK_ENDPOINT", None)

REGION = "us-east-1"

_TABLE_KWARGS = {
    "TableName": "pixelvault-images",
    "KeySchema": [{"AttributeName": "image_id", "KeyType": "HASH"}],
    "AttributeDefinitions": [
        {"AttributeName": "image_id", "AttributeType": "S"},
        {"AttributeName": "user_id", "AttributeType": "S"},
        {"AttributeName": "upload_date", "AttributeType": "S"},
    ],
    "GlobalSecondaryIndexes": [
        {
            "IndexName": "UserIdIndex",
            "KeySchema": [
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "upload_date", "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "ALL"},
            "ProvisionedThroughput": {
                "ReadCapacityUnits": 5,
                "WriteCapacityUnits": 5,
            },
        }
    ],
    "ProvisionedThroughput": {
        "ReadCapacityUnits": 5,
        "WriteCapacityUnits": 5,
    },
}


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = REGION


@pytest.fixture
def aws_env(aws_credentials):
    """Combined fixture: mocked S3 bucket + DynamoDB table."""
    with mock_aws():
        s3 = boto3.client("s3", region_name=REGION)
        s3.create_bucket(Bucket="pixelvault-images")

        resource = boto3.resource("dynamodb", region_name=REGION)
        table = resource.create_table(**_TABLE_KWARGS)
        yield {"s3": s3, "table": table}


def make_upload_event(user_id="user1", filename="test.jpg", content_type="image/jpeg",
                      description="Test image", tags=None, image_bytes=None):
    """Helper to build a valid upload API Gateway event."""
    if tags is None:
        tags = ["test"]
    if image_bytes is None:
        image_bytes = b"fake-image-binary-data"
    return {
        "body": json.dumps({
            "user_id": user_id,
            "filename": filename,
            "content_type": content_type,
            "description": description,
            "tags": tags,
            "image_data": base64.b64encode(image_bytes).decode(),
        }),
    }


def make_list_event(query_params=None):
    """Helper to build a list API Gateway event."""
    return {
        "queryStringParameters": query_params,
    }


def make_get_event(image_id):
    """Helper to build a get-image API Gateway event."""
    return {
        "pathParameters": {"image_id": image_id},
    }


def make_delete_event(image_id):
    """Helper to build a delete-image API Gateway event."""
    return {
        "pathParameters": {"image_id": image_id},
    }


def upload_one(aws_env, **kwargs):
    """Upload a single image and return its metadata dict."""
    from src.handlers.upload import handler as upload_handler
    event = make_upload_event(**kwargs)
    response = upload_handler(event, None)
    return json.loads(response["body"])["image"]
