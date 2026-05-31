"""Lambda handler — List images with optional filters.

GET /images
Query parameters:
  user_id  — filter by uploader (uses GSI)
  tag      — filter by tag (post-filter on scan/query results)
  filename — filter by filename substring
"""
import logging

from boto3.dynamodb.conditions import Key, Attr

from src.utils.aws_clients import get_dynamodb_table
from src.utils.response import success, error, sanitise_items

logger = logging.getLogger(__name__)


def handler(event, context):
    """List images with optional filters: user_id, tag, filename."""
    params = event.get("queryStringParameters") or {}

    user_id = params.get("user_id")
    tag = params.get("tag")
    filename = params.get("filename")

    table = get_dynamodb_table()

    try:
        if user_id:
            items = _query_by_user(table, user_id, tag=tag, filename=filename)
        else:
            items = _scan_all(table, tag=tag, filename=filename)

        items = sanitise_items(items)
        return success({"count": len(items), "images": items})

    except Exception as exc:
        logger.error("Failed to list images: %s", exc)
        return error(f"Failed to list images: {str(exc)}", status_code=500)


def _query_by_user(table, user_id, tag=None, filename=None):
    """Query the UserIdIndex GSI with pagination support."""
    query_kwargs = {
        "IndexName": "UserIdIndex",
        "KeyConditionExpression": Key("user_id").eq(user_id),
    }
    filter_expr = _build_filters(tag=tag, filename=filename)
    if filter_expr:
        query_kwargs["FilterExpression"] = filter_expr

    items = []
    while True:
        response = table.query(**query_kwargs)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        query_kwargs["ExclusiveStartKey"] = last_key
    return items


def _scan_all(table, tag=None, filename=None):
    """Full table scan with pagination support."""
    scan_kwargs = {}
    filter_expr = _build_filters(tag=tag, filename=filename)
    if filter_expr:
        scan_kwargs["FilterExpression"] = filter_expr

    items = []
    while True:
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key
    return items


def _build_filters(tag=None, filename=None):
    """Build a composite DynamoDB FilterExpression from optional filters."""
    expressions = []
    if tag:
        expressions.append(Attr("tags").contains(tag))
    if filename:
        expressions.append(Attr("filename").contains(filename))

    if not expressions:
        return None
    combined = expressions[0]
    for expr in expressions[1:]:
        combined = combined & expr
    return combined
