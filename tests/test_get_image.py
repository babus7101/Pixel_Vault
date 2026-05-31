"""Tests for the get image handler."""
import json

import pytest

from tests.conftest import make_get_event, upload_one
from src.handlers.get_image import handler as get_handler


class TestGetImageHandler:
    """Get/download image handler tests."""

    def test_get_existing_image(self, aws_env):
        """Should return metadata and download URL for an existing image."""
        image = upload_one(aws_env)
        event = make_get_event(image["image_id"])
        response = get_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["image"]["image_id"] == image["image_id"]
        assert body["image"]["filename"] == "test.jpg"
        assert "download_url" in body["image"]
        assert body["image"]["download_url"].startswith("https://")

    def test_get_nonexistent_image(self, aws_env):
        """Should return 404 for a non-existent image_id."""
        event = make_get_event("nonexistent-id")
        response = get_handler(event, None)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert "not found" in body["error"].lower()

    def test_get_missing_path_param(self, aws_env):
        """Should return 400 when image_id is missing from path."""
        event = {
            "httpMethod": "GET",
            "path": "/images/",
            "pathParameters": None,
        }
        response = get_handler(event, None)
        assert response["statusCode"] == 400

    def test_get_returns_all_metadata(self, aws_env):
        """Should include all metadata fields."""
        image = upload_one(aws_env, description="Beautiful sunset", tags=["nature"])
        event = make_get_event(image["image_id"])
        response = get_handler(event, None)

        body = json.loads(response["body"])
        img = body["image"]
        assert img["description"] == "Beautiful sunset"
        assert img["tags"] == ["nature"]
        assert img["content_type"] == "image/jpeg"
        assert isinstance(img["file_size"], int)
        assert "upload_date" in img
        assert "s3_key" in img

    def test_get_empty_path_params(self, aws_env):
        """Should return 400 when pathParameters is an empty dict."""
        event = {
            "httpMethod": "GET",
            "path": "/images/",
            "pathParameters": {},
        }
        response = get_handler(event, None)
        assert response["statusCode"] == 400

    def test_get_cors_headers(self, aws_env):
        """Response should include CORS headers."""
        image = upload_one(aws_env)
        event = make_get_event(image["image_id"])
        response = get_handler(event, None)
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"
