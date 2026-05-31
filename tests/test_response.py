"""Tests for the response utility module."""
import decimal
import json

from src.utils.response import success, error, sanitise_item, sanitise_items


class TestResponseHelpers:
    """Response helper function tests."""

    def test_success_default_status(self):
        """Success with default status code 200."""
        resp = success({"key": "value"})
        assert resp["statusCode"] == 200
        assert json.loads(resp["body"]) == {"key": "value"}
        assert resp["headers"]["Content-Type"] == "application/json"
        assert resp["headers"]["Access-Control-Allow-Origin"] == "*"

    def test_success_custom_status(self):
        """Success with custom status code."""
        resp = success({"created": True}, status_code=201)
        assert resp["statusCode"] == 201

    def test_error_default_status(self):
        """Error with default status code 400."""
        resp = error("bad request")
        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert body["error"] == "bad request"

    def test_error_custom_status(self):
        """Error with custom 500 status code."""
        resp = error("internal", status_code=500)
        assert resp["statusCode"] == 500

    def test_error_cors_headers(self):
        """Error responses should include CORS headers."""
        resp = error("test")
        assert resp["headers"]["Access-Control-Allow-Origin"] == "*"


class TestSanitiseItem:
    """Decimal sanitisation tests."""

    def test_decimal_integer(self):
        """Decimal whole numbers should become int."""
        item = {"size": decimal.Decimal("1024")}
        result = sanitise_item(item)
        assert result["size"] == 1024
        assert isinstance(result["size"], int)

    def test_decimal_float(self):
        """Decimal with fractional part should become float."""
        item = {"ratio": decimal.Decimal("3.14")}
        result = sanitise_item(item)
        assert result["ratio"] == 3.14
        assert isinstance(result["ratio"], float)

    def test_non_decimal_passthrough(self):
        """Non-Decimal values should pass through unchanged."""
        item = {"name": "test", "tags": ["a", "b"], "count": 5}
        result = sanitise_item(item)
        assert result == item

    def test_mixed_types(self):
        """Mixed Decimal and non-Decimal values."""
        item = {
            "name": "photo.jpg",
            "file_size": decimal.Decimal("2048"),
            "tags": ["nature"],
        }
        result = sanitise_item(item)
        assert result["name"] == "photo.jpg"
        assert result["file_size"] == 2048
        assert isinstance(result["file_size"], int)
        assert result["tags"] == ["nature"]

    def test_empty_item(self):
        """Empty dict should return empty dict."""
        assert sanitise_item({}) == {}


class TestSanitiseItems:
    """Batch Decimal sanitisation tests."""

    def test_multiple_items(self):
        """Should sanitise all items in list."""
        items = [
            {"size": decimal.Decimal("100")},
            {"size": decimal.Decimal("200")},
        ]
        result = sanitise_items(items)
        assert len(result) == 2
        assert result[0]["size"] == 100
        assert result[1]["size"] == 200

    def test_empty_list(self):
        """Empty list should return empty list."""
        assert sanitise_items([]) == []
