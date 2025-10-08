# Go API Documentation

**Complete documentation for the Go REST API service**

---

## 🎯 Overview

The Go API is the central service that handles all HTTP requests, authentication, job management, and coordinates with workers. It's built with Fiber (fast HTTP framework) and provides a RESTful interface for the Article Extraction System.

---

## 🏗️ Architecture

### **Core Components**
```mermaid
graph TD
    A[HTTP Layer<br/>Fiber web framework] --> B[Middleware<br/>Auth, Rate Limiting, Logging]
    B --> C[Handlers<br/>Request/Response handling]
    C --> D[Services<br/>Business logic]
    D --> E[Repositories<br/>Data access layer]
    E --> F[Database<br/>PostgreSQL + Redis]
```

### **Request Flow**
```mermaid
sequenceDiagram
    participant Client
    participant Middleware
    participant Handler
    participant Service
    participant Repository
    participant Database

    Client->>Middleware: HTTP Request
    Middleware->>Handler: Processed Request
    Handler->>Service: Business Logic
    Service->>Repository: Data Access
    Repository->>Database: Query/Update
    Database-->>Repository: Result
    Repository-->>Service: Data
    Service-->>Handler: Business Result
    Handler-->>Middleware: Response
    Middleware-->>Client: HTTP Response (JSON)
```

---

## 📁 Project Structure

```
api/
├── cmd/api/main.go              # Application entry point
├── internal/
│   ├── config/                 # Configuration management
│   │   └── config.go
│   ├── database/               # Database connections
│   │   ├── postgres.go
│   │   └── redis.go
│   ├── handlers/               # HTTP handlers
│   │   ├── auth.go
│   │   ├── extract.go
│   │   ├── jobs.go
│   │   └── websocket.go
│   ├── middleware/             # HTTP middleware
│   │   ├── auth.go
│   │   ├── logger.go
│   │   └── ratelimit.go
│   ├── models/                 # Data models
│   │   ├── user.go
│   │   ├── job.go
│   │   └── site_config.go
│   ├── repository/             # Data access layer
│   │   ├── user_repo.go
│   │   ├── job_repo.go
│   │   └── config_repo.go
│   ├── service/                # Business logic
│   │   ├── auth_service.go
│   │   ├── job_service.go
│   │   └── queue_service.go
│   └── websocket/              # WebSocket handling
│       └── hub.go
└── tests/                      # Test files
```

---

## 🔧 Configuration

### **Environment Variables**
```env
# Server
API_PORT=8080
API_HOST=0.0.0.0
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/article_extraction
DB_HOST=localhost
DB_PORT=5432
DB_USER=article_user
DB_PASSWORD=secure_password
DB_NAME=article_extraction
DB_MAX_CONNECTIONS=25
DB_MIN_CONNECTIONS=5

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Authentication
JWT_SECRET=your-super-secret-jwt-key
JWT_EXPIRY_HOURS=24
BCRYPT_COST=10

# AI Services
GEMINI_API_KEY=your_gemini_api_key

# Queue
QUEUE_CONCURRENCY=10
QUEUE_GO_WORKER_COUNT=5
QUEUE_PYTHON_WORKER_COUNT=2

# Rate Limiting
RATE_LIMIT_FREE=10
RATE_LIMIT_PRO=100
RATE_LIMIT_WINDOW=60

# Logging
LOG_LEVEL=info
LOG_FORMAT=json
```

### **Configuration Loading**
```go
// internal/config/config.go
type Config struct {
    Server   ServerConfig
    Database DatabaseConfig
    Redis    RedisConfig
    Queue    QueueConfig
    Auth     AuthConfig
    Gemini   GeminiConfig
    RateLimit RateLimitConfig
    Logging  LoggingConfig
}

func Load() (*Config, error) {
    // Load from environment variables
    // Validate required fields
    // Set defaults
}
```

---

## 🚀 API Endpoints

### **Health Check**
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "article-extraction-api",
  "version": "1.0.0"
}
```

### **Authentication**

#### **Register User**
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

#### **Login User**
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

#### **Get Current User**
```http
GET /api/v1/auth/me
Authorization: Bearer <token>
```

### **Article Extraction**

#### **Extract Single Article**
```http
POST /api/v1/extract/single
Authorization: Bearer <token>
Content-Type: application/json

{
  "url": "https://example.com/article"
}
```

#### **Extract Multiple Articles**
```http
POST /api/v1/extract/batch
Authorization: Bearer <token>
Content-Type: application/json

{
  "urls": [
    "https://example.com/article1",
    "https://example.com/article2"
  ]
}
```

### **Job Management**

#### **Get Job Status**
```http
GET /api/v1/jobs/{job_id}
Authorization: Bearer <token>
```

#### **List User Jobs**
```http
GET /api/v1/jobs?limit=20&offset=0
Authorization: Bearer <token>
```

### **WebSocket**
```http
GET /api/v1/ws
Authorization: Bearer <token>
```

---

## 🔐 Authentication System

### **JWT Token Structure**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "tier": "free",
  "exp": 1640995200,
  "iat": 1640908800
}
```

### **API Key Authentication**
```http
X-API-Key: ak_live_a1b2c3d4e5f6g7h8i9j0
```

### **Password Hashing**
```go
// bcrypt with configurable cost
hashedPassword, err := bcrypt.GenerateFromPassword([]byte(password), bcryptCost)
```

---

## 🗄️ Database Models

### **User Model**
```go
type User struct {
    ID           uuid.UUID  `json:"id" db:"id"`
    Email        string     `json:"email" db:"email"`
    PasswordHash string     `json:"-" db:"password_hash"`
    Tier         UserTier   `json:"tier" db:"tier"`
    Credits      int        `json:"credits" db:"credits"`
    APIKey       *string    `json:"api_key,omitempty" db:"api_key"`
    CreatedAt    time.Time  `json:"created_at" db:"created_at"`
    UpdatedAt    time.Time  `json:"updated_at" db:"updated_at"`
    LastLoginAt  *time.Time `json:"last_login_at,omitempty" db:"last_login_at"`
    IsActive     bool       `json:"is_active" db:"is_active"`
}
```

### **Job Model**
```go
type Job struct {
    ID               uuid.UUID  `json:"id" db:"id"`
    UserID           uuid.UUID  `json:"user_id" db:"user_id"`
    URL              string     `json:"url" db:"url"`
    Domain           string     `json:"domain" db:"domain"`
    Status           JobStatus  `json:"status" db:"status"`
    WorkerType       *string    `json:"worker_type,omitempty" db:"worker_type"`
    ProgressPercent  int        `json:"progress_percent" db:"progress_percent"`
    ProgressMessage  *string    `json:"progress_message,omitempty" db:"progress_message"`
    ResultPath       *string    `json:"result_path,omitempty" db:"result_path"`
    MarkdownContent  *string    `json:"markdown_content,omitempty" db:"markdown_content"`
    Title            *string    `json:"title,omitempty" db:"title"`
    Author           *string    `json:"author,omitempty" db:"author"`
    PublishedAt      *time.Time `json:"published_at,omitempty" db:"published_at"`
    WordCount        *int       `json:"word_count,omitempty" db:"word_count"`
    ImageCount       *int       `json:"image_count,omitempty" db:"image_count"`
    ErrorMessage     *string    `json:"error_message,omitempty" db:"error_message"`
    RetryCount       int        `json:"retry_count" db:"retry_count"`
    QueuedAt         time.Time  `json:"queued_at" db:"queued_at"`
    StartedAt        *time.Time `json:"started_at,omitempty" db:"started_at"`
    CompletedAt      *time.Time `json:"completed_at,omitempty" db:"completed_at"`
    CreditsUsed      int        `json:"credits_used" db:"credits_used"`
    CreatedAt        time.Time  `json:"created_at" db:"created_at"`
    UpdatedAt        time.Time  `json:"updated_at" db:"updated_at"`
}
```

### **Site Config Model**
```go
type SiteConfig struct {
    ID                    uuid.UUID  `json:"id" db:"id"`
    Domain                string     `json:"domain" db:"domain"`
    ConfigYAML            string     `json:"config_yaml" db:"config_yaml"`
    RequiresBrowser       bool       `json:"requires_browser" db:"requires_browser"`
    LearnedByUserID       *uuid.UUID `json:"learned_by_user_id,omitempty" db:"learned_by_user_id"`
    LearnedAt             time.Time  `json:"learned_at" db:"learned_at"`
    LearnIterations       int        `json:"learn_iterations" db:"learn_iterations"`
    SuccessCount          int        `json:"success_count" db:"success_count"`
    FailureCount          int        `json:"failure_count" db:"failure_count"`
    LastUsedAt            *time.Time `json:"last_used_at,omitempty" db:"last_used_at"`
    Version               int        `json:"version" db:"version"`
    Notes                 *string    `json:"notes,omitempty" db:"notes"`
    CreatedAt             time.Time  `json:"created_at" db:"created_at"`
    UpdatedAt             time.Time  `json:"updated_at" db:"updated_at"`
    AvgExtractionTimeMs   *int       `json:"avg_extraction_time_ms,omitempty" db:"avg_extraction_time_ms"`
}
```

---

## 🔄 Job Processing Flow

### **Job Lifecycle**
```
1. Job Created → Status: queued
2. Job Picked Up → Status: processing
3. Site Learning → Status: learning (if needed)
4. Content Extraction → Status: extracting
5. AI Processing → Status: generating_descriptions
6. Job Complete → Status: completed
7. Job Failed → Status: failed
```

### **Worker Assignment**
```go
// Determine worker type based on site requirements
func (s *JobService) determineWorkerType(domain string) string {
    config, err := s.configRepo.GetByDomain(ctx, domain)
    if err != nil {
        return "go" // Default to Go worker
    }
    
    if config.RequiresBrowser {
        return "python" // Use Python worker for JS-heavy sites
    }
    
    return "go" // Use Go worker for simple sites
}
```

---

## 🚦 Rate Limiting

### **Rate Limit Configuration**
```go
type RateLimitConfig struct {
    Free   int           // 10 requests per hour
    Pro    int           // 100 requests per hour
    Window time.Duration // 1 hour window
}
```

### **Rate Limit Implementation**
```go
func RateLimit(rdb *redis.Client, cfg *config.RateLimitConfig) fiber.Handler {
    return func(c *fiber.Ctx) error {
        user := c.Locals("user").(*models.User)
        
        // Determine limit based on user tier
        var limit int
        switch user.Tier {
        case models.TierFree:
            limit = cfg.Free
        case models.TierPro:
            limit = cfg.Pro
        }
        
        // Check current usage
        key := fmt.Sprintf("ratelimit:%s:%s", user.ID, time.Now().Format("2006-01-02-15"))
        count, err := rdb.Incr(ctx, key).Result()
        
        if count > int64(limit) {
            return c.Status(429).JSON(fiber.Map{
                "error": "Rate limit exceeded",
                "limit": limit,
                "retry_after": cfg.Window.Seconds(),
            })
        }
        
        return c.Next()
    }
}
```

---

## 🔌 WebSocket Integration

### **WebSocket Hub**
```go
type Hub struct {
    clients    map[*Client]bool
    register   chan *Client
    unregister chan *Client
    broadcast  chan []byte
}

func (h *Hub) Run() {
    for {
        select {
        case client := <-h.register:
            h.clients[client] = true
            
        case client := <-h.unregister:
            if _, ok := h.clients[client]; ok {
                delete(h.clients, client)
                close(client.send)
            }
            
        case message := <-h.broadcast:
            for client := range h.clients {
                select {
                case client.send <- message:
                default:
                    close(client.send)
                    delete(h.clients, client)
                }
            }
        }
    }
}
```

### **Real-time Updates**
```go
// Send job progress updates
func (h *Hub) BroadcastJobUpdate(jobID string, progress int, message string) {
    update := JobUpdate{
        JobID:    jobID,
        Progress: progress,
        Message:  message,
        Timestamp: time.Now(),
    }
    
    data, _ := json.Marshal(update)
    h.broadcast <- data
}
```

---

## 🧪 Testing

### **Unit Tests**
```go
func TestAuthHandler_Login(t *testing.T) {
    // Setup test database
    db := setupTestDB(t)
    defer cleanupTestDB(t, db)
    
    // Create test user
    user := createTestUser(t, db)
    
    // Test login
    handler := NewAuthHandler(authService)
    req := models.LoginRequest{
        Email:    user.Email,
        Password: "password123",
    }
    
    // Mock request
    c := createTestContext(t, req)
    err := handler.Login(c)
    
    assert.NoError(t, err)
    assert.Equal(t, 200, c.Response().StatusCode())
}
```

### **Integration Tests**
```go
func TestExtractWorkflow(t *testing.T) {
    // Setup test environment
    api := setupTestAPI(t)
    defer api.Close()
    
    // Register user
    user := registerTestUser(t, api)
    
    // Extract article
    job := extractArticle(t, api, user.Token, "https://example.com/article")
    
    // Wait for completion
    waitForJobCompletion(t, api, user.Token, job.ID)
    
    // Verify result
    result := getJobResult(t, api, user.Token, job.ID)
    assert.Equal(t, "completed", result.Status)
    assert.NotEmpty(t, result.MarkdownContent)
}
```

---

## 🚀 Deployment

### **Docker Configuration**
```dockerfile
FROM golang:1.21-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN go build -o bin/api cmd/api/main.go

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/

COPY --from=builder /app/bin/api .
COPY --from=builder /app/shared/db/migrations ./migrations

EXPOSE 8080
CMD ["./api"]
```

### **Environment Configuration**
```yaml
# docker-compose.yml
services:
  api:
    build: ./api
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/article_extraction
      - REDIS_HOST=redis
      - JWT_SECRET=your-secret-key
      - GEMINI_API_KEY=your-gemini-key
    ports:
      - "8080:8080"
    depends_on:
      - postgres
      - redis
```

---

## 📊 Monitoring

### **Health Checks**
```go
func healthCheck(c *fiber.Ctx) error {
    // Check database connection
    if err := db.Ping(); err != nil {
        return c.Status(503).JSON(fiber.Map{
            "status": "unhealthy",
            "database": "down",
        })
    }
    
    // Check Redis connection
    if err := redis.Ping(ctx).Err(); err != nil {
        return c.Status(503).JSON(fiber.Map{
            "status": "unhealthy",
            "redis": "down",
        })
    }
    
    return c.JSON(fiber.Map{
        "status": "healthy",
        "timestamp": time.Now(),
    })
}
```

### **Metrics Collection**
```go
// Request metrics
func Logger() fiber.Handler {
    return func(c *fiber.Ctx) error {
        start := time.Now()
        
        err := c.Next()
        
        log.Info().
            Str("method", c.Method()).
            Str("path", c.Path()).
            Int("status", c.Response().StatusCode()).
            Dur("latency", time.Since(start)).
            Msg("Request")
            
        return err
    }
}
```

---

## 🔧 Development

### **Running Locally**
```bash
# Start dependencies
docker-compose up -d postgres redis

# Run migrations
go run cmd/api/main.go migrate

# Start API server
go run cmd/api/main.go
```

### **Code Generation**
```bash
# Generate mocks
mockgen -source=internal/service/auth_service.go -destination=internal/mocks/auth_service_mock.go

# Generate API docs
swag init -g cmd/api/main.go
```

---

## 📚 Next Steps

- **[React Frontend Documentation](react-frontend.md)** - Frontend integration
- **[Worker Documentation](workers.md)** - Go and Python workers
- **[System Integration](system-integration.md)** - How all parts work together
- **[Deployment Guide](deployment.md)** - Production deployment

---

**The Go API provides the foundation for the entire Article Extraction System!**
