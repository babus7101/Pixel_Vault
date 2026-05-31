"""Tests for the delete image handler."""
import json

import pytest

from tests.conftest import make_delete_event, make_get_event, upload_one
from src.handlers.delete_image import handler as delete_handler
from src.handlers.get_image import handler as get_handler


class TestDeleteImageHandler:
    """Delete image handler tests."""

    def test_delete_existing_image(self, aws_env):
        """Should return 200 and remove the image."""
        image = upload_one(aws_env)
        event = make_delete_event(image["image_id"])
        response = delete_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["message"] == "Image deleted successfully"
        assert body["image_id"] == image["image_id"]

    def test_delete_removes_from_dynamodb(self, aws_env):
        """After deletion, the image metadata should not exist."""
        image = upload_one(aws_env)
        delete_handler(make_delete_event(image["image_id"]), None)

        result = aws_env["table"].get_item(Key={"image_id": image["image_id"]})
        assert "Item" not in result

    def test_delete_removes_from_s3(self, aws_env):
        """After deletion, the S3 object should not exist."""
        image = upload_one(aws_env)
        s3_key = image["s3_key"]
        delete_handler(make_delete_event(image["image_id"]), None)

        with pytest.raises(Exception):
            aws_env["s3"].get_object(Bucket="pixelvault-images", Key=s3_key)

    def test_delete_nonexistent_image(self, aws_env):
        """Should return 404 for a non-existent image_id."""
        event = make_delete_event("nonexistent-id")
        response = delete_handler(event, None)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert "not found" in body["error"].lower()

    def test_delete_missing_path_param(self, aws_env):
        """Should return 400 when image_id is missing from path."""
        event = {
            "httpMethod": "DELETE",
            "path": "/images/",
            "pathParameters": None,
        }
        response = delete_handler(event, None)
        assert response["statusCode"] == 400

    def test_delete_then_get_returns_404(self, aws_env):
        """After deletion, GET for the same image should return 404."""
        image = upload_one(aws_env)
        delete_handler(make_delete_event(image["image_id"]), None)

        get_response = get_handler(make_get_event(image["image_id"]), None)
        assert get_response["statusCode"] == 404

    def test_delete_one_does_not_affect_others(self, aws_env):
        """Deleting one image should not affect other images."""
        image1 = upload_one(aws_env, filename="img1.jpg")
        image2 = upload_one(aws_env, filename="img2.jpg")

        delete_handler(make_delete_event(image1["image_id"]), None)

        # image2 should still exist
        get_response = get_handler(make_get_event(image2["image_id"]), None)
        assert get_response["statusCode"] == 200

    def test_delete_empty_path_params(self, aws_env):
        """Should return 400 when pathParameters is an empty dict."""
        event = {
            "httpMethod": "DELETE",
            "path": "/images/",
            "pathParameters": {},
        }
        response = delete_handler(event, None)
        assert response["statusCode"] == 400

    def test_delete_cors_headers(self, aws_env):
        """Response should include CORS headers."""
        image = upload_one(aws_env)
        event = make_delete_event(image["image_id"])
        response = delete_handler(event, None)
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"
