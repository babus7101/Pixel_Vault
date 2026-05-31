"""Tests for the list images handler."""
import json

import pytest

from tests.conftest import make_upload_event, make_list_event
from src.handlers.upload import handler as upload_handler
from src.handlers.list_images import handler as list_handler


def _seed_images(aws_env):
    """Upload several images for list/filter tests."""
    images = [
        {"user_id": "alice", "filename": "sunset.jpg", "tags": ["nature", "sunset"]},
        {"user_id": "alice", "filename": "mountain.png", "tags": ["nature", "mountain"], "content_type": "image/png"},
        {"user_id": "bob", "filename": "cat.jpg", "tags": ["pets", "cat"]},
        {"user_id": "bob", "filename": "dog.jpg", "tags": ["pets", "dog"]},
        {"user_id": "charlie", "filename": "food.jpg", "tags": ["food"]},
    ]
    uploaded = []
    for img in images:
        event = make_upload_event(**img)
        resp = upload_handler(event, None)
        uploaded.append(json.loads(resp["body"])["image"])
    return uploaded


class TestListImagesHandler:
    """List images handler tests."""

    def test_list_all_images(self, aws_env):
        """Should return all images when no filters are applied."""
        _seed_images(aws_env)
        event = make_list_event()
        response = list_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 5
        assert len(body["images"]) == 5

    def test_list_empty(self, aws_env):
        """Should return empty list when no images exist."""
        event = make_list_event()
        response = list_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 0
        assert body["images"] == []

    def test_filter_by_user_id(self, aws_env):
        """Should return only images for the specified user."""
        _seed_images(aws_env)
        event = make_list_event({"user_id": "alice"})
        response = list_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 2
        for img in body["images"]:
            assert img["user_id"] == "alice"

    def test_filter_by_tag(self, aws_env):
        """Should return only images containing the specified tag."""
        _seed_images(aws_env)
        event = make_list_event({"tag": "nature"})
        response = list_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 2
        for img in body["images"]:
            assert "nature" in img["tags"]

    def test_filter_by_user_id_and_tag(self, aws_env):
        """Should combine user_id and tag filters."""
        _seed_images(aws_env)
        event = make_list_event({"user_id": "alice", "tag": "sunset"})
        response = list_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 1
        assert body["images"][0]["filename"] == "sunset.jpg"

    def test_filter_by_filename(self, aws_env):
        """Should filter images by filename substring."""
        _seed_images(aws_env)
        event = make_list_event({"filename": "cat"})
        response = list_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 1
        assert body["images"][0]["filename"] == "cat.jpg"

    def test_filter_by_tag_and_filename(self, aws_env):
        """Should combine tag and filename filters."""
        _seed_images(aws_env)
        event = make_list_event({"tag": "pets", "filename": "dog"})
        response = list_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 1
        assert body["images"][0]["filename"] == "dog.jpg"

    def test_filter_no_match(self, aws_env):
        """Should return empty list when no images match the filter."""
        _seed_images(aws_env)
        event = make_list_event({"user_id": "nonexistent"})
        response = list_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 0

    def test_filter_by_user_id_bob(self, aws_env):
        """Should return Bob's images."""
        _seed_images(aws_env)
        event = make_list_event({"user_id": "bob"})
        response = list_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 2
        filenames = {img["filename"] for img in body["images"]}
        assert filenames == {"cat.jpg", "dog.jpg"}

    def test_null_query_params(self, aws_env):
        """Should handle None queryStringParameters gracefully."""
        _seed_images(aws_env)
        event = {"httpMethod": "GET", "path": "/images", "queryStringParameters": None}
        response = list_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 5

    def test_response_includes_file_size(self, aws_env):
        """Listed images should include file_size as an integer."""
        _seed_images(aws_env)
        event = make_list_event()
        response = list_handler(event, None)
        body = json.loads(response["body"])
        for img in body["images"]:
            assert isinstance(img["file_size"], int)

    def test_cors_headers(self, aws_env):
        """Response should include CORS headers."""
        event = make_list_event()
        response = list_handler(event, None)
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"
