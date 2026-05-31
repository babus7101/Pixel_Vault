# PixelVault API Documentation

## Base URL

```
http://localhost:4566/restapis/{api-id}/dev/_user_request_
```

> The `{api-id}` is printed by `deploy_localstack.sh` after deployment.

---

## Endpoints

### 1. Upload Image

Upload an image with metadata.

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/images` |
| **Content-Type** | `application/json` |

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | string | ✅ | Uploader's user identifier |
| `filename` | string | ✅ | Original filename (e.g. `sunset.jpg`) |
| `image_data` | string | ✅ | Base64-encoded image binary |
| `content_type` | string | ❌ | MIME type. Default: `image/jpeg`. Allowed: `image/jpeg`, `image/png`, `image/gif`, `image/webp` |
| `description` | string | ❌ | Description text |
| `tags` | string[] | ❌ | List of tags |

#### Example Request

```bash
# Encode an image to base64
IMAGE_B64=$(base64 -i photo.jpg)

curl -X POST "${BASE_URL}/images" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "filename": "sunset.jpg",
    "content_type": "image/jpeg",
    "description": "Golden hour at the beach",
    "tags": ["nature", "sunset", "beach"],
    "image_data": "'"${IMAGE_B64}"'"
  }'
```

#### Success Response — `201 Created`

```json
{
  "message": "Image uploaded successfully",
  "image": {
    "image_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "user_id": "alice",
    "filename": "sunset.jpg",
    "content_type": "image/jpeg",
    "description": "Golden hour at the beach",
    "tags": ["nature", "sunset", "beach"],
    "s3_key": "alice/a1b2c3d4-e5f6-7890-abcd-ef1234567890/sunset.jpg",
    "upload_date": "2026-05-29T13:15:00+00:00",
    "file_size": 204800
  }
}
```

#### Error Responses

| Status | Condition |
|--------|-----------|
| `400` | Missing required field (`user_id`, `filename`, `image_data`) |
| `400` | Unsupported `content_type` |
| `400` | Invalid base64 in `image_data` |
| `400` | File exceeds 10 MB limit |
| `400` | Malformed JSON body |

---

### 2. List Images

Retrieve images with optional filters. Supports filtering by `user_id`, `tag`, and `filename`.

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/images` |

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | string | Filter by uploader (uses DynamoDB GSI for efficiency) |
| `tag` | string | Filter by tag (e.g. `nature`) |
| `filename` | string | Filter by filename substring |

All filters are optional and can be combined.

#### Example Requests

```bash
# List all images
curl "${BASE_URL}/images"

# Filter by user
curl "${BASE_URL}/images?user_id=alice"

# Filter by tag
curl "${BASE_URL}/images?tag=nature"

# Combine filters
curl "${BASE_URL}/images?user_id=alice&tag=sunset"

# Filter by filename
curl "${BASE_URL}/images?filename=sunset"
```

#### Success Response — `200 OK`

```json
{
  "count": 2,
  "images": [
    {
      "image_id": "a1b2c3d4-...",
      "user_id": "alice",
      "filename": "sunset.jpg",
      "content_type": "image/jpeg",
      "description": "Golden hour at the beach",
      "tags": ["nature", "sunset", "beach"],
      "s3_key": "alice/a1b2c3d4-.../sunset.jpg",
      "upload_date": "2026-05-29T13:15:00+00:00",
      "file_size": 204800
    },
    {
      "image_id": "b2c3d4e5-...",
      "user_id": "alice",
      "filename": "mountain.png",
      "content_type": "image/png",
      "description": "Hiking trip",
      "tags": ["nature", "mountain"],
      "s3_key": "alice/b2c3d4e5-.../mountain.png",
      "upload_date": "2026-05-29T14:00:00+00:00",
      "file_size": 512000
    }
  ]
}
```

---

### 3. Get / Download Image

Retrieve image metadata and a pre-signed S3 download URL (valid for 1 hour).

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/images/{image_id}` |

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `image_id` | string | ✅ | UUID of the image |

#### Example Request

```bash
curl "${BASE_URL}/images/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

#### Success Response — `200 OK`

```json
{
  "image": {
    "image_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "user_id": "alice",
    "filename": "sunset.jpg",
    "content_type": "image/jpeg",
    "description": "Golden hour at the beach",
    "tags": ["nature", "sunset", "beach"],
    "s3_key": "alice/a1b2c3d4-.../sunset.jpg",
    "upload_date": "2026-05-29T13:15:00+00:00",
    "file_size": 204800,
    "download_url": "https://pixelvault-images.s3.amazonaws.com/alice/a1b2c3d4-.../sunset.jpg?X-Amz-..."
  }
}
```

#### Error Responses

| Status | Condition |
|--------|-----------|
| `400` | Missing `image_id` path parameter |
| `404` | Image not found |

---

### 4. Delete Image

Permanently delete an image from S3 and its metadata from DynamoDB.

| | |
|---|---|
| **Method** | `DELETE` |
| **Path** | `/images/{image_id}` |

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `image_id` | string | ✅ | UUID of the image |

#### Example Request

```bash
curl -X DELETE "${BASE_URL}/images/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

#### Success Response — `200 OK`

```json
{
  "message": "Image deleted successfully",
  "image_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

#### Error Responses

| Status | Condition |
|--------|-----------|
| `400` | Missing `image_id` path parameter |
| `404` | Image not found |

---

## Error Response Format

All error responses follow a consistent format:

```json
{
  "error": "Human-readable error message"
}
```

## CORS

All endpoints return `Access-Control-Allow-Origin: *` to support browser-based clients.
