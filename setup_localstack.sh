#!/usr/bin/env bash
# setup_localstack.sh — Provision AWS resources in LocalStack
set -euo pipefail

ENDPOINT="http://localhost:4566"
REGION="us-east-1"
BUCKET_NAME="pixelvault-images"
TABLE_NAME="pixelvault-images"

export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=$REGION

echo "==> Creating S3 bucket: $BUCKET_NAME"
aws --endpoint-url="$ENDPOINT" s3 mb "s3://$BUCKET_NAME" 2>/dev/null || echo "Bucket already exists"

echo "==> Creating DynamoDB table: $TABLE_NAME"
aws --endpoint-url="$ENDPOINT" dynamodb create-table \
    --table-name "$TABLE_NAME" \
    --attribute-definitions \
        AttributeName=image_id,AttributeType=S \
        AttributeName=user_id,AttributeType=S \
        AttributeName=upload_date,AttributeType=S \
    --key-schema \
        AttributeName=image_id,KeyType=HASH \
    --global-secondary-indexes \
        '[
            {
                "IndexName": "UserIdIndex",
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "upload_date", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5}
            }
        ]' \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
    2>/dev/null || echo "Table already exists"

echo "==> LocalStack resources provisioned successfully"
echo ""
echo "S3 Bucket:      $BUCKET_NAME"
echo "DynamoDB Table:  $TABLE_NAME"
echo "Endpoint:        $ENDPOINT"
