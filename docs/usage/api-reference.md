# REST API Reference

**Complete API documentation for the Article Extraction Service**

---

## 🚀 Quick Start

### **Base URL**
```
http://localhost:8080/api/v1
```

### **Authentication**
All endpoints (except auth) require authentication via:
- **JWT Token**: `Authorization: Bearer <token>`
- **API Key**: `X-API-Key: <api_key>`

---

## 🔐 Authentication

### **Register User**
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "tier": "free",
    "credits": 10,
    "api_key": "ak_live_...",
    "created_at": "2025-01-02T15:30:00Z"
  }
}
```

### **Login User**
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "tier": "free",
    "credits": 9
  }
}
```

### **Get Current User**
```http
GET /api/v1/auth/me
Authorization: Bearer <token>
```

**Response:**
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "tier": "free",
    "credits": 9,
    "api_key": "ak_live_...",
    "created_at": "2025-01-02T15:30:00Z"
  }
}
```

---

## 📄 Article Extraction

### **Extract Single Article**
```http
POST /api/v1/extract/single
Authorization: Bearer <token>
Content-Type: application/json

{
  "url": "https://example.com/article"
}
```

**Response:**
```json
{
  "job": {
    "id": "uuid",
    "url": "https://example.com/article",
    "domain": "example.com",
    "status": "queued",
    "progress_percent": 0,
    "credits_used": 1,
    "created_at": "2025-01-02T15:30:00Z"
  },
  "message": "Job queued for processing"
}
```

### **Extract Multiple Articles**
```http
POST /api/v1/extract/batch
Authorization: Bearer <token>
Content-Type: application/json

{
  "urls": [
    "https://example.com/article1",
    "https://example.com/article2",
    "https://example.com/article3"
  ]
}
```

**Response:**
```json
{
  "jobs": [
    {
      "id": "uuid1",
      "url": "https://example.com/article1",
      "status": "queued"
    },
    {
      "id": "uuid2", 
      "url": "https://example.com/article2",
      "status": "queued"
    }
  ],
  "count": 2,
  "message": "Batch jobs queued for processing"
}
```

---

## 📊 Job Management

### **Get Job Status**
```http
GET /api/v1/jobs/{job_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "job": {
    "id": "uuid",
    "url": "https://example.com/article",
    "domain": "example.com",
    "status": "completed",
    "progress_percent": 100,
    "progress_message": "Extraction completed",
    "result_path": "storage/uuid.md",
    "markdown_content": "# Article Title\n\nContent...",
    "title": "Article Title",
    "author": "Author Name",
    "published_at": "2025-01-01T10:00:00Z",
    "word_count": 2500,
    "image_count": 5,
    "credits_used": 1,
    "queued_at": "2025-01-02T15:30:00Z",
    "started_at": "2025-01-02T15:30:05Z",
    "completed_at": "2025-01-02T15:30:15Z"
  }
}
```

### **List User Jobs**
```http
GET /api/v1/jobs?limit=20&offset=0
Authorization: Bearer <token>
```

**Response:**
```json
{
  "jobs": [
    {
      "id": "uuid1",
      "url": "https://example.com/article1",
      "status": "completed",
      "title": "Article 1",
      "created_at": "2025-01-02T15:30:00Z"
    },
    {
      "id": "uuid2",
      "url": "https://example.com/article2", 
      "status": "processing",
      "progress_percent": 50,
      "created_at": "2025-01-02T15:25:00Z"
    }
  ],
  "count": 2
}
```

---

## 📁 File Access

### **Download Extracted Content**
```http
GET /storage/{filename}.md
```

**Response:** Raw Markdown content

### **Get Job Result**
```http
GET /api/v1/jobs/{job_id}/download
Authorization: Bearer <token>
```

**Response:** Raw Markdown content with proper headers

---

## 📊 Status Codes

### **Job Statuses**
- `queued` - Job is waiting to be processed
- `processing` - Job is currently being processed
- `learning` - System is learning how to extract from this site
- `extracting` - Content is being extracted
- `generating_descriptions` - AI is generating image descriptions
- `completed` - Job completed successfully
- `failed` - Job failed with error

### **HTTP Status Codes**
- `200` - Success
- `201` - Created (registration, job creation)
- `400` - Bad Request (invalid input)
- `401` - Unauthorized (invalid token)
- `404` - Not Found (job not found)
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error

---

## 🔒 Rate Limiting

### **Rate Limits by Tier**
- **Free**: 10 requests per hour
- **Pro**: 100 requests per hour
- **Enterprise**: 1000 requests per hour

### **Rate Limit Headers**
```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 8
X-RateLimit-Reset: 1640995200
```

### **Rate Limit Exceeded**
```json
{
  "error": "Rate limit exceeded",
  "limit": 10,
  "window": "1h",
  "retry_after": 3600
}
```

---

## 🧪 Example Workflows

### **Complete Extraction Workflow**
```bash
# 1. Register user
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# 2. Login and get token
TOKEN=$(curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}' \
  | jq -r '.token')

# 3. Extract article
JOB_ID=$(curl -X POST http://localhost:8080/api/v1/extract/single \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/article"}' \
  | jq -r '.job.id')

# 4. Check job status
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/api/v1/jobs/$JOB_ID

# 5. Download result when completed
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/api/v1/jobs/$JOB_ID/download
```

### **Batch Processing Workflow**
```bash
# 1. Create URL list
cat > urls.txt << EOF
https://example.com/article1
https://example.com/article2
https://example.com/article3
EOF

# 2. Process batch
curl -X POST http://localhost:8080/api/v1/extract/batch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"urls":["https://example.com/article1","https://example.com/article2"]}'

# 3. Monitor all jobs
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/api/v1/jobs
```

---

## 🔧 Error Handling

### **Common Errors**

#### **Invalid URL**
```json
{
  "error": "Invalid URL format"
}
```

#### **Insufficient Credits**
```json
{
  "error": "Insufficient credits"
}
```

#### **Job Not Found**
```json
{
  "error": "Job not found"
}
```

#### **Authentication Required**
```json
{
  "error": "Unauthorized"
}
```

### **Error Response Format**
```json
{
  "error": "Error message",
  "details": "Additional error details",
  "code": "ERROR_CODE"
}
```

---

## 📊 Webhooks (Future)

### **Job Status Webhooks**
```http
POST /api/v1/webhooks/job-status
Content-Type: application/json

{
  "job_id": "uuid",
  "status": "completed",
  "url": "https://example.com/article",
  "result_url": "https://api.example.com/storage/uuid.md"
}
```

---

## 🎯 SDK Examples

### **Python SDK**
```python
import requests

# Authentication
response = requests.post('http://localhost:8080/api/v1/auth/login', json={
    'email': 'user@example.com',
    'password': 'password123'
})
token = response.json()['token']

# Extract article
headers = {'Authorization': f'Bearer {token}'}
response = requests.post('http://localhost:8080/api/v1/extract/single', 
    headers=headers, json={'url': 'https://example.com/article'})
job_id = response.json()['job']['id']

# Check status
response = requests.get(f'http://localhost:8080/api/v1/jobs/{job_id}', 
    headers=headers)
print(response.json())
```

### **JavaScript SDK**
```javascript
// Authentication
const response = await fetch('http://localhost:8080/api/v1/auth/login', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        email: 'user@example.com',
        password: 'password123'
    })
});
const {token} = await response.json();

// Extract article
const extractResponse = await fetch('http://localhost:8080/api/v1/extract/single', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({url: 'https://example.com/article'})
});
const {job} = await extractResponse.json();
```

---

## 📚 Next Steps

- **[Web Interface Guide](frontend-interface.md)** - Use the React frontend
- **[System Architecture](../technical/architecture.md)** - Understand the system
- **[Deployment Guide](../technical/deployment.md)** - Deploy to production

---

**Need help?** Check the [error handling section](#error-handling) or see [System Overview](../README.md) for more details.



