#!/usr/bin/env bash
# deploy_localstack.sh — Package Lambda functions and deploy to LocalStack
# with API Gateway integration.
set -euo pipefail

ENDPOINT="http://localhost:4566"
REGION="us-east-1"
ACCOUNT_ID="000000000000"
FUNCTION_PREFIX="pixelvault"
API_NAME="pixelvault-api"

export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=$REGION

echo "==> Packaging Lambda functions..."
PACKAGE_DIR=$(mktemp -d)
cp -r src "$PACKAGE_DIR/"
pip install -r requirements.txt -t "$PACKAGE_DIR/" --quiet 2>/dev/null
(cd "$PACKAGE_DIR" && zip -r9 /tmp/pixelvault-lambda.zip . -x '*.pyc' '__pycache__/*' > /dev/null)
rm -rf "$PACKAGE_DIR"

# IAM role (LocalStack doesn't enforce IAM, but the API requires it)
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/lambda-role"

create_function() {
    local func_name="$1"
    local handler_path="$2"

    echo "  Creating function: $func_name"
    aws --endpoint-url="$ENDPOINT" lambda create-function \
        --function-name "$func_name" \
        --runtime python3.9 \
        --handler "$handler_path" \
        --role "$ROLE_ARN" \
        --zip-file fileb:///tmp/pixelvault-lambda.zip \
        --environment "Variables={S3_BUCKET=pixelvault-images,DYNAMODB_TABLE=pixelvault-images,LOCALSTACK_ENDPOINT=$ENDPOINT}" \
        --timeout 30 \
        --no-cli-pager \
        2>/dev/null || \
    aws --endpoint-url="$ENDPOINT" lambda update-function-code \
        --function-name "$func_name" \
        --zip-file fileb:///tmp/pixelvault-lambda.zip \
        --no-cli-pager 2>/dev/null
}

echo "==> Deploying Lambda functions..."
create_function "${FUNCTION_PREFIX}-upload"      "src.handlers.upload.handler"
create_function "${FUNCTION_PREFIX}-list"        "src.handlers.list_images.handler"
create_function "${FUNCTION_PREFIX}-get"         "src.handlers.get_image.handler"
create_function "${FUNCTION_PREFIX}-delete"      "src.handlers.delete_image.handler"

echo ""
echo "==> Creating API Gateway..."

# Create REST API
API_ID=$(aws --endpoint-url="$ENDPOINT" apigateway create-rest-api \
    --name "$API_NAME" \
    --query 'id' --output text 2>/dev/null)

ROOT_ID=$(aws --endpoint-url="$ENDPOINT" apigateway get-resources \
    --rest-api-id "$API_ID" \
    --query 'items[?path==`/`].id' --output text)

# /images resource
IMAGES_ID=$(aws --endpoint-url="$ENDPOINT" apigateway create-resource \
    --rest-api-id "$API_ID" \
    --parent-id "$ROOT_ID" \
    --path-part "images" \
    --query 'id' --output text)

# /images/{image_id} resource
IMAGE_ID=$(aws --endpoint-url="$ENDPOINT" apigateway create-resource \
    --rest-api-id "$API_ID" \
    --parent-id "$IMAGES_ID" \
    --path-part "{image_id}" \
    --query 'id' --output text)

setup_method() {
    local resource_id="$1"
    local http_method="$2"
    local function_name="$3"

    aws --endpoint-url="$ENDPOINT" apigateway put-method \
        --rest-api-id "$API_ID" \
        --resource-id "$resource_id" \
        --http-method "$http_method" \
        --authorization-type "NONE" \
        --no-cli-pager 2>/dev/null

    FUNCTION_ARN="arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${function_name}"

    aws --endpoint-url="$ENDPOINT" apigateway put-integration \
        --rest-api-id "$API_ID" \
        --resource-id "$resource_id" \
        --http-method "$http_method" \
        --type AWS_PROXY \
        --integration-http-method POST \
        --uri "arn:aws:apigateway:${REGION}:lambda:path/2015-03-31/functions/${FUNCTION_ARN}/invocations" \
        --no-cli-pager 2>/dev/null
}

echo "  POST   /images"
setup_method "$IMAGES_ID" "POST" "${FUNCTION_PREFIX}-upload"

echo "  GET    /images"
setup_method "$IMAGES_ID" "GET" "${FUNCTION_PREFIX}-list"

echo "  GET    /images/{image_id}"
setup_method "$IMAGE_ID" "GET" "${FUNCTION_PREFIX}-get"

echo "  DELETE /images/{image_id}"
setup_method "$IMAGE_ID" "DELETE" "${FUNCTION_PREFIX}-delete"

# Deploy
aws --endpoint-url="$ENDPOINT" apigateway create-deployment \
    --rest-api-id "$API_ID" \
    --stage-name "dev" \
    --no-cli-pager 2>/dev/null

echo ""
echo "==> Deployment complete!"
echo ""
echo "API Base URL: ${ENDPOINT}/restapis/${API_ID}/dev/_user_request_"
echo ""
echo "Endpoints:"
echo "  POST   ${ENDPOINT}/restapis/${API_ID}/dev/_user_request_/images"
echo "  GET    ${ENDPOINT}/restapis/${API_ID}/dev/_user_request_/images"
echo "  GET    ${ENDPOINT}/restapis/${API_ID}/dev/_user_request_/images/{image_id}"
echo "  DELETE ${ENDPOINT}/restapis/${API_ID}/dev/_user_request_/images/{image_id}"

# Clean up
rm -f /tmp/pixelvault-lambda.zip
