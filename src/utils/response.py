"""Standardised HTTP response helpers for API Gateway Lambda proxy integration."""
import decimal
import json


_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
}


def success(body, status_code=200):
    return {
        "statusCode": status_code,
        "headers": dict(_HEADERS),
        "body": json.dumps(body),
    }


def error(message, status_code=400):
    return {
        "statusCode": status_code,
        "headers": dict(_HEADERS),
        "body": json.dumps({"error": message}),
    }


def sanitise_item(item):
    """Convert DynamoDB Decimal values to native Python int/float."""
    clean = {}
    for k, v in item.items():
        if isinstance(v, decimal.Decimal):
            clean[k] = int(v) if v == int(v) else float(v)
        else:
            clean[k] = v
    return clean


def sanitise_items(items):
    """Convert DynamoDB Decimal values in a list of items."""
    return [sanitise_item(item) for item in items]
