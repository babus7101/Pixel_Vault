# PixelVault API

A serverless image upload and storage service (Instagram-like) built with AWS Lambda, API Gateway, S3, and DynamoDB. Uses [LocalStack](https://localstack.cloud/) for local development.

## Architecture

```
Client ──▶ API Gateway ──▶ Lambda Functions ──▶ S3 (image storage)
                                             ──▶ DynamoDB (metadata)
```

| Component | Purpose |
|-----------|---------|
| **API Gateway** | HTTP routing to Lambda functions |
| **Lambda** (Python 3.7+) | Business logic for each endpoint |
| **S3** | Binary image file storage |
| **DynamoDB** | Image metadata (user, tags, timestamps, etc.) |
| **LocalStack** | Local AWS emulation via Docker |

## Prerequisites

- Python 3.7+
- Docker & Docker Compose
- AWS CLI v2

## Quick Start

### 1. Start LocalStack

```bash
docker-compose up -d
```

Wait a few seconds for LocalStack to initialise.

### 2. Provision AWS Resources

```bash
chmod +x setup_localstack.sh
./setup_localstack.sh
```

This creates the S3 bucket (`pixelvault-images`) and DynamoDB table (`pixelvault-images`).

### 3. Deploy Lambda Functions & API Gateway

```bash
pip install -r requirements.txt
chmod +x deploy_localstack.sh
./deploy_localstack.sh
```

The script prints the API base URL. Example:

```
API Base URL: http://localhost:4566/restapis/abc123def/dev/_user_request_
```

### 4. Try It Out

```bash
# Set the base URL (use the one printed by deploy script)
export BASE_URL="http://localhost:4566/restapis/<api-id>/dev/_user_request_"

# Upload an image
IMAGE_B64=$(base64 -i path/to/photo.jpg)
curl -s -X POST "${BASE_URL}/images" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "filename": "photo.jpg",
    "content_type": "image/jpeg",
    "description": "My first upload",
    "tags": ["test"],
    "image_data": "'"${IMAGE_B64}"'"
  }' | python -m json.tool

# List all images
curl -s "${BASE_URL}/images" | python -m json.tool

# Filter by user
curl -s "${BASE_URL}/images?user_id=alice" | python -m json.tool

# Filter by tag
curl -s "${BASE_URL}/images?tag=test" | python -m json.tool

# Get a specific image (replace <image_id>)
curl -s "${BASE_URL}/images/<image_id>" | python -m json.tool

# Delete an image
curl -s -X DELETE "${BASE_URL}/images/<image_id>" | python -m json.tool
```

## Development

### Install Dependencies

```bash
pip install -r requirements-dev.txt
```

### Run Tests

```bash
python -m pytest tests/ -v
```

Tests use [moto](https://github.com/getmoto/moto) to mock AWS services — no Docker or LocalStack needed.

### Run Tests with Coverage

```bash
python -m pytest tests/ -v --cov=src --cov-report=term-missing
```
## API Reference

See [API.md](API.md) for complete endpoint documentation with request/response examples.

### Endpoints Summary

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/images` | Upload image with metadata |
| `GET` | `/images` | List images (filter by `user_id`, `tag`, `filename`) |
| `GET` | `/images/{image_id}` | Get metadata + pre-signed download URL |
| `DELETE` | `/images/{image_id}` | Delete image from S3 and DynamoDB |

## DynamoDB Schema

| Attribute | Type | Key |
|-----------|------|-----|
| `image_id` | String | Partition Key |
| `user_id` | String | GSI Partition Key |
| `upload_date` | String (ISO 8601) | GSI Sort Key |
| `filename` | String | — |
| `content_type` | String | — |
| `description` | String | — |
| `tags` | List\<String\> | — |
| `s3_key` | String | — |
| `file_size` | Number | — |

## Scalability

- **Lambda** auto-scales horizontally per request — handles concurrent users
- **DynamoDB** with provisioned throughput (adjustable) or on-demand mode
- **S3** natively scales to any volume of image storage
- **API Gateway** handles throttling and request routing
