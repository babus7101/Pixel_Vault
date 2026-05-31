"""Tests for the upload handler."""
import base64
import json

import pytest

from tests.conftest import make_upload_event
from src.handlers.upload import handler


class TestUploadHandler:
    """Upload image handler tests."""

    def test_successful_upload(self, aws_env):
        """A valid upload should return 201 with image metadata."""
        event = make_upload_event()
        response = handler(event, None)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["message"] == "Image uploaded successfully"
        image = body["image"]
        assert image["user_id"] == "user1"
        assert image["filename"] == "test.jpg"
        assert image["content_type"] == "image/jpeg"
        assert image["description"] == "Test image"
        assert image["tags"] == ["test"]
        assert "image_id" in image
        assert "s3_key" in image
        assert "upload_date" in image
        assert image["file_size"] > 0

    def test_upload_stores_in_s3(self, aws_env):
        """The image binary should be stored in S3."""
        image_bytes = b"hello-image-world"
        event = make_upload_event(image_bytes=image_bytes)
        response = handler(event, None)

        body = json.loads(response["body"])
        s3_key = body["image"]["s3_key"]

        obj = aws_env["s3"].get_object(Bucket="pixelvault-images", Key=s3_key)
        assert obj["Body"].read() == image_bytes

    def test_upload_stores_in_dynamodb(self, aws_env):
        """The metadata should be persisted in DynamoDB."""
        event = make_upload_event()
        response = handler(event, None)

        body = json.loads(response["body"])
        image_id = body["image"]["image_id"]

        item = aws_env["table"].get_item(Key={"image_id": image_id}).get("Item")
        assert item is not None
        assert item["user_id"] == "user1"
        assert item["filename"] == "test.jpg"

    def test_upload_missing_user_id(self, aws_env):
        """Should return 400 when user_id is missing."""
        event = {
            "body": json.dumps({
                "filename": "test.jpg",
                "image_data": base64.b64encode(b"data").decode(),
            })
        }
        response = handler(event, None)
        assert response["statusCode"] == 400
        assert "user_id is required" in json.loads(response["body"])["error"]

    def test_upload_missing_filename(self, aws_env):
        """Should return 400 when filename is missing."""
        event = {
            "body": json.dumps({
                "user_id": "user1",
                "image_data": base64.b64encode(b"data").decode(),
            })
        }
        response = handler(event, None)
        assert response["statusCode"] == 400
        assert "filename is required" in json.loads(response["body"])["error"]

    def test_upload_missing_image_data(self, aws_env):
        """Should return 400 when image_data is missing."""
        event = {
            "body": json.dumps({
                "user_id": "user1",
                "filename": "test.jpg",
            })
        }
        response = handler(event, None)
        assert response["statusCode"] == 400
        assert "image_data is required" in json.loads(response["body"])["error"]

    def test_upload_invalid_content_type(self, aws_env):
        """Should return 400 for unsupported content types."""
        event = make_upload_event(content_type="application/pdf")
        response = handler(event, None)
        assert response["statusCode"] == 400
        assert "Unsupported content_type" in json.loads(response["body"])["error"]

    def test_upload_invalid_base64(self, aws_env):
        """Should return 400 when image_data is not valid base64."""
        event = {
            "body": json.dumps({
                "user_id": "user1",
                "filename": "test.jpg",
                "image_data": "not-valid-base64!!!",
            })
        }
        response = handler(event, None)
        assert response["statusCode"] == 400
        assert "valid base64" in json.loads(response["body"])["error"]

    def test_upload_invalid_json_body(self, aws_env):
        """Should return 400 when body is not valid JSON."""
        event = {"body": "not json at all"}
        response = handler(event, None)
        assert response["statusCode"] == 400
        assert "Invalid JSON" in json.loads(response["body"])["error"]

    def test_upload_no_body(self, aws_env):
        """Should return 400 when body is None."""
        event = {"body": None}
        response = handler(event, None)
        assert response["statusCode"] == 400

    def test_upload_file_too_large(self, aws_env):
        """Should return 400 when image exceeds size limit."""
        large_data = b"x" * (10 * 1024 * 1024 + 1)  # Just over 10 MB
        event = make_upload_event(image_bytes=large_data)
        response = handler(event, None)
        assert response["statusCode"] == 400
        assert "exceeds maximum size" in json.loads(response["body"])["error"]

    def test_upload_with_png(self, aws_env):
        """Should accept PNG images."""
        event = make_upload_event(content_type="image/png", filename="photo.png")
        response = handler(event, None)
        assert response["statusCode"] == 201

    def test_upload_with_gif(self, aws_env):
        """Should accept GIF images."""
        event = make_upload_event(content_type="image/gif", filename="anim.gif")
        response = handler(event, None)
        assert response["statusCode"] == 201

    def test_upload_with_webp(self, aws_env):
        """Should accept WebP images."""
        event = make_upload_event(content_type="image/webp", filename="photo.webp")
        response = handler(event, None)
        assert response["statusCode"] == 201

    def test_upload_empty_tags(self, aws_env):
        """Should accept an upload with empty tags list."""
        event = make_upload_event(tags=[])
        response = handler(event, None)
        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["image"]["tags"] == []

    def test_upload_multiple_tags(self, aws_env):
        """Should store multiple tags."""
        event = make_upload_event(tags=["nature", "sunset", "landscape"])
        response = handler(event, None)
        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["image"]["tags"] == ["nature", "sunset", "landscape"]

    def test_upload_cors_headers(self, aws_env):
        """Response should include CORS headers."""
        event = make_upload_event()
        response = handler(event, None)
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"

    def test_upload_unique_ids(self, aws_env):
        """Each upload should get a unique image_id."""
        event1 = make_upload_event(filename="img1.jpg")
        event2 = make_upload_event(filename="img2.jpg")
        r1 = handler(event1, None)
        r2 = handler(event2, None)
        id1 = json.loads(r1["body"])["image"]["image_id"]
        id2 = json.loads(r2["body"])["image"]["image_id"]
        assert id1 != id2

    # --- New security / edge-case tests ---

    def test_upload_path_traversal_filename(self, aws_env):
        """Filename with path traversal should be sanitised."""
        event = make_upload_event(filename="../../etc/passwd")
        response = handler(event, None)
        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["image"]["filename"] == "passwd"
        assert "../" not in body["image"]["s3_key"]

    def test_upload_empty_body(self, aws_env):
        """Empty JSON object should return 400."""
        event = {"body": "{}"}
        response = handler(event, None)
        assert response["statusCode"] == 400

    def test_upload_non_string_user_id(self, aws_env):
        """Non-string user_id should be rejected."""
        event = {
            "body": json.dumps({
                "user_id": 12345,
                "filename": "test.jpg",
                "image_data": base64.b64encode(b"data").decode(),
            })
        }
        response = handler(event, None)
        assert response["statusCode"] == 400

    def test_upload_non_list_tags(self, aws_env):
        """Non-list tags should be rejected."""
        event = {
            "body": json.dumps({
                "user_id": "user1",
                "filename": "test.jpg",
                "image_data": base64.b64encode(b"data").decode(),
                "tags": "not-a-list",
            })
        }
        response = handler(event, None)
        assert response["statusCode"] == 400
        assert "tags must be a list" in json.loads(response["body"])["error"]

    def test_upload_too_many_tags(self, aws_env):
        """Should reject uploads with more than MAX_TAGS tags."""
        event = {
            "body": json.dumps({
                "user_id": "user1",
                "filename": "test.jpg",
                "image_data": base64.b64encode(b"data").decode(),
                "tags": [f"tag{i}" for i in range(21)],
            })
        }
        response = handler(event, None)
        assert response["statusCode"] == 400
        assert "Maximum" in json.loads(response["body"])["error"]

    def test_upload_empty_image_data(self, aws_env):
        """Empty base64 (decodes to 0 bytes) should be rejected."""
        event = {
            "body": json.dumps({
                "user_id": "user1",
                "filename": "test.jpg",
                "image_data": "",
            })
        }
        response = handler(event, None)
        assert response["statusCode"] == 400

    def test_upload_filename_only_traversal_dots(self, aws_env):
        """Filename that resolves to empty after sanitisation should be rejected."""
        event = {
            "body": json.dumps({
                "user_id": "user1",
                "filename": "../..",
                "image_data": base64.b64encode(b"data").decode(),
            })
        }
        response = handler(event, None)
        assert response["statusCode"] == 400

    def test_upload_missing_event_body_key(self, aws_env):
        """Event with no body key should handle gracefully."""
        event = {}
        response = handler(event, None)
        assert response["statusCode"] == 400

    def test_upload_s3_key_format(self, aws_env):
        """S3 key should follow user_id/image_id/filename format."""
        event = make_upload_event(user_id="alice", filename="sunset.jpg")
        response = handler(event, None)
        body = json.loads(response["body"])
        s3_key = body["image"]["s3_key"]
        parts = s3_key.split("/")
        assert len(parts) == 3
        assert parts[0] == "alice"
        assert parts[2] == "sunset.jpg"
