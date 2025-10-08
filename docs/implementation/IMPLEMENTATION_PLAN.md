# Article Extraction Service - Implementation Plan

**Version:** 1.0  
**Date:** October 2, 2025  
**Architecture:** Go API + Go Workers + Python AI Workers

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Technology Stack](#technology-stack)
3. [Project Structure](#project-structure)
4. [Implementation Phases](#implementation-phases)
5. [Testing Strategy](#testing-strategy)
6. [Configuration Management](#configuration-management)
7. [Local Development Setup](#local-development-setup)
8. [Deployment Strategy](#deployment-strategy)

---

## Project Overview

### Architecture Summary

```mermaid
graph TB
    subgraph "Article Extraction Service"
        subgraph "API Layer"
            GoAPI[Go API<br/>Port 8080<br/>User-facing REST API<br/>Handles auth, job creation, status]
        end
        
        subgraph "Queue Layer"
            Queue[Cloud Tasks / Redis Queue<br/>Job queue]
        end
        
        subgraph "Worker Layer"
            GoWorker[Go Worker<br/>Fast processing]
            PythonWorker[Python AI Worker<br/>AI-powered learning]
        end
        
        subgraph "Data Layer"
            PostgreSQL[(PostgreSQL<br/>Database)]
            Redis[(Redis<br/>Cache & Queue)]
            Storage[(Storage<br/>File system)]
        end
        
        GoAPI --> Queue
        Queue --> GoWorker
        Queue --> PythonWorker
        GoWorker --> PostgreSQL
        PythonWorker --> PostgreSQL
        GoWorker --> Redis
        PythonWorker --> Redis
        GoWorker --> Storage
        PythonWorker --> Storage
    end
```

### Core Principles

1. **Start Simple:** Local development with minimal dependencies
2. **Test Each Layer:** Every component has clear test criteria
3. **Incremental Build:** Each phase produces working, testable code
4. **Configuration Driven:** All environment-specific values in `.env`
5. **Docker Ready:** Containerization from day 1

---

## Technology Stack

### Go Services
- **API Framework:** Fiber v2 (fast, Express-like)
- **Database:** pgx v5 (PostgreSQL driver)
- **Redis:** go-redis v9
- **HTML Parsing:** goquery
- **HTTP Client:** resty v2
- **Job Queue:** asynq (Redis-based)
- **Config:** viper + godotenv
- **Testing:** testify + httptest
- **Validation:** go-playground/validator
- **Logging:** zerolog

### Python Services
- **Framework:** FastAPI
- **Browser:** Playwright
- **AI:** google-generativeai
- **HTML:** BeautifulSoup4
- **Config:** python-dotenv
- **Testing:** pytest + pytest-asyncio

### Infrastructure
- **Database:** PostgreSQL 15+
- **Cache/Queue:** Redis 7+
- **Storage:** Local filesystem (dev), Cloud Storage (prod)
- **Container:** Docker + Docker Compose

---

## Project Structure

```
article-extraction-service/
├── api/                          # Go API Server
│   ├── main.go
│   ├── go.mod
│   ├── go.sum
│   ├── cmd/
│   │   └── api/
│   │       └── main.go
│   ├── internal/
│   │   ├── config/
│   │   │   └── config.go        # Load .env, validate config
│   │   ├── middleware/
│   │   │   ├── auth.go
│   │   │   ├── ratelimit.go
│   │   │   └── logger.go
│   │   ├── handlers/
│   │   │   ├── auth.go          # POST /auth/register, /auth/login
│   │   │   ├── extract.go       # POST /extract/single, /extract/batch
│   │   │   ├── jobs.go          # GET /jobs/:id
│   │   │   └── websocket.go     # WS /ws/:userId
│   │   ├── models/
│   │   │   ├── user.go
│   │   │   ├── job.go
│   │   │   └── site_config.go
│   │   ├── repository/
│   │   │   ├── user_repo.go
│   │   │   ├── job_repo.go
│   │   │   └── config_repo.go
│   │   ├── service/
│   │   │   ├── auth_service.go
│   │   │   ├── job_service.go
│   │   │   └── queue_service.go
│   │   └── database/
│   │       ├── postgres.go
│   │       └── redis.go
│   └── tests/
│       ├── integration/
│       └── unit/
│
├── worker-go/                    # Go Fast Path Worker
│   ├── main.go
│   ├── go.mod
│   ├── go.sum
│   ├── cmd/
│   │   └── worker/
│   │       └── main.go
│   ├── internal/
│   │   ├── config/
│   │   │   └── config.go
│   │   ├── extractor/
│   │   │   ├── fetcher.go       # HTTP fetching
│   │   │   ├── parser.go        # goquery parsing
│   │   │   └── processor.go     # Image processing
│   │   ├── gemini/
│   │   │   └── client.go        # Gemini API client
│   │   ├── worker/
│   │   │   └── handler.go       # Job processing logic
│   │   └── repository/
│   │       └── config_repo.go
│   └── tests/
│
├── worker-python/                # Python AI Worker
│   ├── main.py
│   ├── requirements.txt
│   ├── src/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── api.py               # FastAPI endpoints
│   │   ├── site_registry.py     # Existing learning logic
│   │   ├── browser.py           # Playwright wrapper
│   │   └── worker.py            # Job handler
│   └── tests/
│       └── test_learning.py
│
├── shared/                       # Shared code/types
│   ├── proto/                   # gRPC definitions (optional)
│   └── db/
│       └── migrations/          # SQL migrations
│           ├── 001_init.sql
│           ├── 002_users.sql
│           ├── 003_jobs.sql
│           └── 004_site_configs.sql
│
├── docker/
│   ├── api.Dockerfile
│   ├── worker-go.Dockerfile
│   ├── worker-python.Dockerfile
│   └── docker-compose.yml
│
├── config/
│   ├── .env.example
│   ├── .env.test
│   └── config.yaml              # Non-secret config
│
├── scripts/
│   ├── setup.sh                 # Setup local environment
│   ├── migrate.sh               # Run DB migrations
│   ├── test-all.sh              # Run all tests
│   └── dev-start.sh             # Start all services locally
│
├── docs/
│   ├── IMPLEMENTATION_PLAN.md   # This file
│   ├── API.md                   # API documentation
│   └── ARCHITECTURE.md
│
├── cloudbuild.yaml              # Google Cloud Build config
├── .gitignore
└── README.md
```

---

## Implementation Phases

### Phase 0: Project Setup (2 hours)

#### Tasks

**0.1 Create Project Structure**
```bash
mkdir -p article-extraction-service/{api,worker-go,worker-python,shared/db/migrations,config,docker,scripts,docs}
cd article-extraction-service
```

**0.2 Initialize Go Modules**
```bash
# API
cd api
go mod init github.com/Denter-/article-extraction/api
go get github.com/gofiber/fiber/v2
go get github.com/jackc/pgx/v5
go get github.com/redis/go-redis/v9
go get github.com/hibiken/asynq
go get github.com/spf13/viper
go get github.com/joho/godotenv
go get github.com/PuerkitoBio/goquery
go get github.com/go-playground/validator/v10
go get github.com/rs/zerolog
go get github.com/golang-jwt/jwt/v5
go get golang.org/x/crypto/bcrypt
go get github.com/google/uuid
cd ..

# Worker
cd worker-go
go mod init github.com/Denter-/article-extraction/worker
# Add same dependencies as API (subset needed)
cd ..
```

**0.3 Create Configuration Files**

`.env.example`:
```env
# Server
API_PORT=8080
API_HOST=0.0.0.0
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/article_extraction?sslmode=disable
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=article_extraction
DB_MAX_CONNECTIONS=25
DB_MIN_CONNECTIONS=5

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Queue
QUEUE_CONCURRENCY=10
QUEUE_GO_WORKER_COUNT=5
QUEUE_PYTHON_WORKER_COUNT=2

# Auth
JWT_SECRET=your-super-secret-jwt-key-change-in-production
JWT_EXPIRY_HOURS=24
BCRYPT_COST=10

# API Keys
GEMINI_API_KEY=your_gemini_api_key_here

# Python Service
PYTHON_WORKER_URL=http://localhost:8081

# Storage
STORAGE_TYPE=local
STORAGE_PATH=./storage
# For Cloud Storage (production):
# STORAGE_TYPE=gcs
# STORAGE_BUCKET=article-extraction-results

# Rate Limiting
RATE_LIMIT_FREE=10
RATE_LIMIT_PRO=100
RATE_LIMIT_WINDOW=60

# Logging
LOG_LEVEL=debug
LOG_FORMAT=json

# Feature Flags
ENABLE_WEBSOCKET=true
ENABLE_BATCH=true
```

**0.4 Create Database Setup Script**

`scripts/setup.sh`:
```bash
#!/bin/bash
set -e

echo "🚀 Setting up Article Extraction Service..."

# Check prerequisites
command -v go >/dev/null 2>&1 || { echo "❌ Go not installed"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python3 not installed"; exit 1; }
command -v psql >/dev/null 2>&1 || { echo "❌ PostgreSQL not installed"; exit 1; }
command -v redis-cli >/dev/null 2>&1 || { echo "❌ Redis not installed"; exit 1; }

# Create .env if not exists
if [ ! -f config/.env ]; then
    echo "📝 Creating .env from example..."
    cp config/.env.example config/.env
    echo "⚠️  Please edit config/.env with your settings"
fi

# Setup PostgreSQL database
echo "🗄️  Setting up PostgreSQL database..."
psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'article_extraction'" | grep -q 1 || \
    psql -U postgres -c "CREATE DATABASE article_extraction"

echo "📊 Running migrations..."
for migration in shared/db/migrations/*.sql; do
    echo "   Running $(basename $migration)..."
    psql -U postgres -d article_extraction -f "$migration"
done

# Setup Python environment
echo "🐍 Setting up Python environment..."
cd worker-python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cd ..

# Test connections
echo "🔍 Testing connections..."
redis-cli ping > /dev/null && echo "✅ Redis connected" || echo "❌ Redis connection failed"
psql -U postgres -d article_extraction -c "SELECT 1" > /dev/null && echo "✅ PostgreSQL connected" || echo "❌ PostgreSQL connection failed"

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit config/.env with your Gemini API key"
echo "  2. Run: ./scripts/dev-start.sh"
```

**0.5 Testing Phase 0**

✅ **Success Criteria:**
- Project structure created
- Go modules initialized
- `.env` file exists
- PostgreSQL database created
- Redis accessible at localhost:6379
- Python venv created

**Test Commands:**
```bash
# Verify structure
ls -la api/ worker-go/ worker-python/

# Verify Go modules
cd api && go mod verify && cd ..

# Verify database
psql -U postgres -d article_extraction -c "SELECT version();"

# Verify Redis
redis-cli ping

# Verify Python
source worker-python/venv/bin/activate && python --version
```

---

### Phase 1: Database Schema & Migrations (2 hours)

#### Tasks

**1.1 Create Migration Files**

`shared/db/migrations/001_init.sql`:
```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';
```

`shared/db/migrations/002_users.sql`:
```sql
-- User tiers enum
CREATE TYPE user_tier AS ENUM ('free', 'pro', 'enterprise');

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    tier user_tier DEFAULT 'free',
    credits INTEGER DEFAULT 10,
    api_key VARCHAR(64) UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_api_key ON users(api_key);
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

`shared/db/migrations/003_jobs.sql`:
```sql
-- Job status enum
CREATE TYPE job_status AS ENUM (
    'queued',
    'processing',
    'learning',
    'extracting',
    'generating_descriptions',
    'completed',
    'failed'
);

-- Extraction jobs table
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    domain VARCHAR(255) NOT NULL,
    status job_status DEFAULT 'queued',
    worker_type VARCHAR(50), -- 'go' or 'python'
    
    -- Progress tracking
    progress_percent INTEGER DEFAULT 0,
    progress_message TEXT,
    
    -- Results
    result_path TEXT, -- Path in storage
    markdown_content TEXT,
    
    -- Metadata
    title TEXT,
    author TEXT,
    published_at TIMESTAMP WITH TIME ZONE,
    word_count INTEGER,
    image_count INTEGER,
    
    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Timing
    queued_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Cost tracking
    credits_used INTEGER DEFAULT 1,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_jobs_user_id ON jobs(user_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_domain ON jobs(domain);
CREATE INDEX idx_jobs_created_at ON jobs(created_at DESC);
CREATE TRIGGER update_jobs_updated_at BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

`shared/db/migrations/004_site_configs.sql`:
```sql
-- Site configurations table
CREATE TABLE site_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain VARCHAR(255) UNIQUE NOT NULL,
    
    -- Configuration
    config_yaml TEXT NOT NULL, -- Full YAML config
    requires_browser BOOLEAN DEFAULT FALSE,
    
    -- Learning metadata
    learned_by_user_id UUID REFERENCES users(id),
    learned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    learn_iterations INTEGER DEFAULT 1,
    
    -- Usage stats
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE,
    
    -- Version control
    version INTEGER DEFAULT 1,
    notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Performance metrics
    avg_extraction_time_ms INTEGER
);

CREATE INDEX idx_site_configs_domain ON site_configs(domain);
CREATE INDEX idx_site_configs_requires_browser ON site_configs(requires_browser);
CREATE TRIGGER update_site_configs_updated_at BEFORE UPDATE ON site_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

`shared/db/migrations/005_usage_logs.sql`:
```sql
-- Usage tracking for analytics and billing
CREATE TABLE usage_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
    
    action VARCHAR(50) NOT NULL, -- 'extract', 'learn', 'api_call'
    credits_charged INTEGER DEFAULT 0,
    
    -- Request metadata
    ip_address INET,
    user_agent TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX idx_usage_logs_created_at ON usage_logs(created_at DESC);
```

**1.2 Testing Phase 1**

✅ **Success Criteria:**
- All migrations run without errors
- Tables created with correct schema
- Indexes created
- Triggers working

**Test Commands:**
```bash
# Run migrations
./scripts/migrate.sh

# Verify tables
psql -U postgres -d article_extraction -c "\dt"

# Verify schema
psql -U postgres -d article_extraction -c "\d users"
psql -U postgres -d article_extraction -c "\d jobs"
psql -U postgres -d article_extraction -c "\d site_configs"

# Test trigger
psql -U postgres -d article_extraction -c "
INSERT INTO users (email, password_hash) VALUES ('test@example.com', 'hash');
SELECT created_at, updated_at FROM users WHERE email = 'test@example.com';
"

# Cleanup test data
psql -U postgres -d article_extraction -c "DELETE FROM users WHERE email = 'test@example.com';"
```

---

### Phase 2: Go API - Core Setup (4 hours)

#### Tasks

**2.1 Configuration Module**

`api/internal/config/config.go`:
```go
package config

import (
    "fmt"
    "os"
    "time"

    "github.com/joho/godotenv"
    "github.com/spf13/viper"
)

type Config struct {
    Server   ServerConfig
    Database DatabaseConfig
    Redis    RedisConfig
    Queue    QueueConfig
    Auth     AuthConfig
    Gemini   GeminiConfig
    Storage  StorageConfig
    RateLimit RateLimitConfig
    Logging  LoggingConfig
}

type ServerConfig struct {
    Port        string
    Host        string
    Environment string
}

type DatabaseConfig struct {
    URL            string
    Host           string
    Port           int
    User           string
    Password       string
    Database       string
    MaxConnections int
    MinConnections int
}

type RedisConfig struct {
    Host     string
    Port     int
    Password string
    DB       int
}

type QueueConfig struct {
    Concurrency        int
    GoWorkerCount      int
    PythonWorkerCount  int
}

type AuthConfig struct {
    JWTSecret      string
    JWTExpiryHours int
    BcryptCost     int
}

type GeminiConfig struct {
    APIKey string
}

type StorageConfig struct {
    Type   string // "local" or "gcs"
    Path   string // For local
    Bucket string // For GCS
}

type RateLimitConfig struct {
    Free   int
    Pro    int
    Window time.Duration
}

type LoggingConfig struct {
    Level  string
    Format string
}

func Load() (*Config, error) {
    // Load .env file if exists
    if err := godotenv.Load("config/.env"); err != nil {
        // Not fatal - might be using environment variables
        fmt.Println("Warning: .env file not found, using environment variables")
    }

    viper.AutomaticEnv()

    cfg := &Config{
        Server: ServerConfig{
            Port:        getEnv("API_PORT", "8080"),
            Host:        getEnv("API_HOST", "0.0.0.0"),
            Environment: getEnv("ENVIRONMENT", "development"),
        },
        Database: DatabaseConfig{
            URL:            getEnv("DATABASE_URL", ""),
            Host:           getEnv("DB_HOST", "localhost"),
            Port:           getEnvInt("DB_PORT", 5432),
            User:           getEnv("DB_USER", "postgres"),
            Password:       getEnv("DB_PASSWORD", "postgres"),
            Database:       getEnv("DB_NAME", "article_extraction"),
            MaxConnections: getEnvInt("DB_MAX_CONNECTIONS", 25),
            MinConnections: getEnvInt("DB_MIN_CONNECTIONS", 5),
        },
        Redis: RedisConfig{
            Host:     getEnv("REDIS_HOST", "localhost"),
            Port:     getEnvInt("REDIS_PORT", 6379),
            Password: getEnv("REDIS_PASSWORD", ""),
            DB:       getEnvInt("REDIS_DB", 0),
        },
        Queue: QueueConfig{
            Concurrency:       getEnvInt("QUEUE_CONCURRENCY", 10),
            GoWorkerCount:     getEnvInt("QUEUE_GO_WORKER_COUNT", 5),
            PythonWorkerCount: getEnvInt("QUEUE_PYTHON_WORKER_COUNT", 2),
        },
        Auth: AuthConfig{
            JWTSecret:      getEnv("JWT_SECRET", ""),
            JWTExpiryHours: getEnvInt("JWT_EXPIRY_HOURS", 24),
            BcryptCost:     getEnvInt("BCRYPT_COST", 10),
        },
        Gemini: GeminiConfig{
            APIKey: getEnv("GEMINI_API_KEY", ""),
        },
        Storage: StorageConfig{
            Type:   getEnv("STORAGE_TYPE", "local"),
            Path:   getEnv("STORAGE_PATH", "./storage"),
            Bucket: getEnv("STORAGE_BUCKET", ""),
        },
        RateLimit: RateLimitConfig{
            Free:   getEnvInt("RATE_LIMIT_FREE", 10),
            Pro:    getEnvInt("RATE_LIMIT_PRO", 100),
            Window: time.Duration(getEnvInt("RATE_LIMIT_WINDOW", 60)) * time.Second,
        },
        Logging: LoggingConfig{
            Level:  getEnv("LOG_LEVEL", "info"),
            Format: getEnv("LOG_FORMAT", "json"),
        },
    }

    if err := cfg.Validate(); err != nil {
        return nil, err
    }

    return cfg, nil
}

func (c *Config) Validate() error {
    if c.Auth.JWTSecret == "" {
        return fmt.Errorf("JWT_SECRET is required")
    }
    if c.Gemini.APIKey == "" {
        return fmt.Errorf("GEMINI_API_KEY is required")
    }
    if c.Database.URL == "" && c.Database.Host == "" {
        return fmt.Errorf("database configuration is required")
    }
    return nil
}

func getEnv(key, defaultValue string) string {
    if value := os.Getenv(key); value != "" {
        return value
    }
    return defaultValue
}

func getEnvInt(key string, defaultValue int) int {
    if value := os.Getenv(key); value != "" {
        var intVal int
        fmt.Sscanf(value, "%d", &intVal)
        return intVal
    }
    return defaultValue
}
```

**2.2 Database Connection**

`api/internal/database/postgres.go`:
```go
package database

import (
    "context"
    "fmt"
    "time"

    "github.com/jackc/pgx/v5/pgxpool"
    "github.com/Denter-/article-extraction/api/internal/config"
)

func NewPostgresPool(cfg *config.DatabaseConfig) (*pgxpool.Pool, error) {
    var connString string
    if cfg.URL != "" {
        connString = cfg.URL
    } else {
        connString = fmt.Sprintf(
            "host=%s port=%d user=%s password=%s dbname=%s sslmode=disable",
            cfg.Host, cfg.Port, cfg.User, cfg.Password, cfg.Database,
        )
    }

    poolConfig, err := pgxpool.ParseConfig(connString)
    if err != nil {
        return nil, fmt.Errorf("unable to parse database config: %w", err)
    }

    poolConfig.MaxConns = int32(cfg.MaxConnections)
    poolConfig.MinConns = int32(cfg.MinConnections)
    poolConfig.MaxConnLifetime = time.Hour
    poolConfig.MaxConnIdleTime = 30 * time.Minute

    ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
    defer cancel()

    pool, err := pgxpool.NewWithConfig(ctx, poolConfig)
    if err != nil {
        return nil, fmt.Errorf("unable to create connection pool: %w", err)
    }

    // Test connection
    if err := pool.Ping(ctx); err != nil {
        return nil, fmt.Errorf("unable to ping database: %w", err)
    }

    return pool, nil
}
```

`api/internal/database/redis.go`:
```go
package database

import (
    "context"
    "fmt"
    "time"

    "github.com/redis/go-redis/v9"
    "github.com/Denter-/article-extraction/api/internal/config"
)

func NewRedisClient(cfg *config.RedisConfig) (*redis.Client, error) {
    client := redis.NewClient(&redis.Options{
        Addr:         fmt.Sprintf("%s:%d", cfg.Host, cfg.Port),
        Password:     cfg.Password,
        DB:           cfg.DB,
        DialTimeout:  5 * time.Second,
        ReadTimeout:  3 * time.Second,
        WriteTimeout: 3 * time.Second,
        PoolSize:     10,
        MinIdleConns: 5,
    })

    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()

    if err := client.Ping(ctx).Err(); err != nil {
        return nil, fmt.Errorf("unable to connect to Redis: %w", err)
    }

    return client, nil
}
```

**2.3 Testing Phase 2**

Create test file: `api/tests/unit/config_test.go`:
```go
package unit

import (
    "os"
    "testing"

    "github.com/stretchr/testify/assert"
    "github.com/Denter-/article-extraction/api/internal/config"
)

func TestLoadConfig(t *testing.T) {
    // Set required env vars
    os.Setenv("JWT_SECRET", "test-secret")
    os.Setenv("GEMINI_API_KEY", "test-key")
    os.Setenv("DATABASE_URL", "postgresql://localhost/test")

    cfg, err := config.Load()
    assert.NoError(t, err)
    assert.NotNil(t, cfg)
    assert.Equal(t, "test-secret", cfg.Auth.JWTSecret)
    assert.Equal(t, "test-key", cfg.Gemini.APIKey)
}

func TestConfigValidation(t *testing.T) {
    cfg := &config.Config{
        Auth: config.AuthConfig{
            JWTSecret: "",
        },
    }

    err := cfg.Validate()
    assert.Error(t, err)
    assert.Contains(t, err.Error(), "JWT_SECRET")
}
```

✅ **Success Criteria:**
- Config loads from .env
- Defaults applied correctly
- Validation catches missing required fields
- PostgreSQL connection established
- Redis connection established

**Test Commands:**
```bash
cd api
go test ./tests/unit/...

# Manual connection test
go run cmd/api/test_connections.go
```

---

### Phase 3: Go API - Models & Repository (3 hours)

#### Tasks

**3.1 Define Models**

`api/internal/models/user.go`:
```go
package models

import (
    "time"

    "github.com/google/uuid"
)

type UserTier string

const (
    TierFree       UserTier = "free"
    TierPro        UserTier = "pro"
    TierEnterprise UserTier = "enterprise"
)

type User struct {
    ID           uuid.UUID  `json:"id" db:"id"`
    Email        string     `json:"email" db:"email" validate:"required,email"`
    PasswordHash string     `json:"-" db:"password_hash"`
    Tier         UserTier   `json:"tier" db:"tier"`
    Credits      int        `json:"credits" db:"credits"`
    APIKey       *string    `json:"api_key,omitempty" db:"api_key"`
    CreatedAt    time.Time  `json:"created_at" db:"created_at"`
    UpdatedAt    time.Time  `json:"updated_at" db:"updated_at"`
    LastLoginAt  *time.Time `json:"last_login_at,omitempty" db:"last_login_at"`
    IsActive     bool       `json:"is_active" db:"is_active"`
}

type CreateUserRequest struct {
    Email    string `json:"email" validate:"required,email"`
    Password string `json:"password" validate:"required,min=8"`
}

type LoginRequest struct {
    Email    string `json:"email" validate:"required,email"`
    Password string `json:"password" validate:"required"`
}

type LoginResponse struct {
    Token string `json:"token"`
    User  User   `json:"user"`
}
```

`api/internal/models/job.go`:
```go
package models

import (
    "time"

    "github.com/google/uuid"
)

type JobStatus string

const (
    StatusQueued                 JobStatus = "queued"
    StatusProcessing             JobStatus = "processing"
    StatusLearning               JobStatus = "learning"
    StatusExtracting             JobStatus = "extracting"
    StatusGeneratingDescriptions JobStatus = "generating_descriptions"
    StatusCompleted              JobStatus = "completed"
    StatusFailed                 JobStatus = "failed"
)

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

type CreateJobRequest struct {
    URL string `json:"url" validate:"required,url"`
}

type CreateBatchJobRequest struct {
    URLs []string `json:"urls" validate:"required,min=1,max=100,dive,url"`
}

type JobResponse struct {
    Job Job `json:"job"`
}

type BatchJobResponse struct {
    Jobs []Job `json:"jobs"`
}
```

`api/internal/models/site_config.go`:
```go
package models

import (
    "time"

    "github.com/google/uuid"
)

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

**3.2 Repository Pattern**

`api/internal/repository/user_repo.go`:
```go
package repository

import (
    "context"
    "fmt"

    "github.com/google/uuid"
    "github.com/jackc/pgx/v5/pgxpool"
    "github.com/Denter-/article-extraction/api/internal/models"
)

type UserRepository struct {
    db *pgxpool.Pool
}

func NewUserRepository(db *pgxpool.Pool) *UserRepository {
    return &UserRepository{db: db}
}

func (r *UserRepository) Create(ctx context.Context, user *models.User) error {
    query := `
        INSERT INTO users (email, password_hash, tier, credits, api_key)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, created_at, updated_at
    `
    return r.db.QueryRow(
        ctx, query,
        user.Email, user.PasswordHash, user.Tier, user.Credits, user.APIKey,
    ).Scan(&user.ID, &user.CreatedAt, &user.UpdatedAt)
}

func (r *UserRepository) GetByEmail(ctx context.Context, email string) (*models.User, error) {
    user := &models.User{}
    query := `
        SELECT id, email, password_hash, tier, credits, api_key,
               created_at, updated_at, last_login_at, is_active
        FROM users
        WHERE email = $1 AND is_active = true
    `
    err := r.db.QueryRow(ctx, query, email).Scan(
        &user.ID, &user.Email, &user.PasswordHash, &user.Tier, &user.Credits,
        &user.APIKey, &user.CreatedAt, &user.UpdatedAt, &user.LastLoginAt, &user.IsActive,
    )
    if err != nil {
        return nil, fmt.Errorf("user not found: %w", err)
    }
    return user, nil
}

func (r *UserRepository) GetByID(ctx context.Context, id uuid.UUID) (*models.User, error) {
    user := &models.User{}
    query := `
        SELECT id, email, password_hash, tier, credits, api_key,
               created_at, updated_at, last_login_at, is_active
        FROM users
        WHERE id = $1 AND is_active = true
    `
    err := r.db.QueryRow(ctx, query, id).Scan(
        &user.ID, &user.Email, &user.PasswordHash, &user.Tier, &user.Credits,
        &user.APIKey, &user.CreatedAt, &user.UpdatedAt, &user.LastLoginAt, &user.IsActive,
    )
    if err != nil {
        return nil, fmt.Errorf("user not found: %w", err)
    }
    return user, nil
}

func (r *UserRepository) GetByAPIKey(ctx context.Context, apiKey string) (*models.User, error) {
    user := &models.User{}
    query := `
        SELECT id, email, password_hash, tier, credits, api_key,
               created_at, updated_at, last_login_at, is_active
        FROM users
        WHERE api_key = $1 AND is_active = true
    `
    err := r.db.QueryRow(ctx, query, apiKey).Scan(
        &user.ID, &user.Email, &user.PasswordHash, &user.Tier, &user.Credits,
        &user.APIKey, &user.CreatedAt, &user.UpdatedAt, &user.LastLoginAt, &user.IsActive,
    )
    if err != nil {
        return nil, fmt.Errorf("user not found: %w", err)
    }
    return user, nil
}

func (r *UserRepository) UpdateCredits(ctx context.Context, userID uuid.UUID, credits int) error {
    query := `UPDATE users SET credits = $1 WHERE id = $2`
    _, err := r.db.Exec(ctx, query, credits, userID)
    return err
}

func (r *UserRepository) UpdateLastLogin(ctx context.Context, userID uuid.UUID) error {
    query := `UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = $1`
    _, err := r.db.Exec(ctx, query, userID)
    return err
}
```

`api/internal/repository/job_repo.go`:
```go
package repository

import (
    "context"
    "fmt"

    "github.com/google/uuid"
    "github.com/jackc/pgx/v5/pgxpool"
    "github.com/Denter-/article-extraction/api/internal/models"
)

type JobRepository struct {
    db *pgxpool.Pool
}

func NewJobRepository(db *pgxpool.Pool) *JobRepository {
    return &JobRepository{db: db}
}

func (r *JobRepository) Create(ctx context.Context, job *models.Job) error {
    query := `
        INSERT INTO jobs (user_id, url, domain, status, credits_used)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, queued_at, created_at, updated_at
    `
    return r.db.QueryRow(
        ctx, query,
        job.UserID, job.URL, job.Domain, job.Status, job.CreditsUsed,
    ).Scan(&job.ID, &job.QueuedAt, &job.CreatedAt, &job.UpdatedAt)
}

func (r *JobRepository) GetByID(ctx context.Context, id uuid.UUID) (*models.Job, error) {
    job := &models.Job{}
    query := `
        SELECT id, user_id, url, domain, status, worker_type,
               progress_percent, progress_message, result_path, markdown_content,
               title, author, published_at, word_count, image_count,
               error_message, retry_count, queued_at, started_at, completed_at,
               credits_used, created_at, updated_at
        FROM jobs
        WHERE id = $1
    `
    err := r.db.QueryRow(ctx, query, id).Scan(
        &job.ID, &job.UserID, &job.URL, &job.Domain, &job.Status, &job.WorkerType,
        &job.ProgressPercent, &job.ProgressMessage, &job.ResultPath, &job.MarkdownContent,
        &job.Title, &job.Author, &job.PublishedAt, &job.WordCount, &job.ImageCount,
        &job.ErrorMessage, &job.RetryCount, &job.QueuedAt, &job.StartedAt, &job.CompletedAt,
        &job.CreditsUsed, &job.CreatedAt, &job.UpdatedAt,
    )
    if err != nil {
        return nil, fmt.Errorf("job not found: %w", err)
    }
    return job, nil
}

func (r *JobRepository) GetByUserID(ctx context.Context, userID uuid.UUID, limit int) ([]*models.Job, error) {
    query := `
        SELECT id, user_id, url, domain, status, worker_type,
               progress_percent, progress_message, result_path,
               title, author, published_at, word_count, image_count,
               error_message, queued_at, started_at, completed_at,
               credits_used, created_at, updated_at
        FROM jobs
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT $2
    `
    rows, err := r.db.Query(ctx, query, userID, limit)
    if err != nil {
        return nil, err
    }
    defer rows.Close()

    jobs := make([]*models.Job, 0)
    for rows.Next() {
        job := &models.Job{}
        err := rows.Scan(
            &job.ID, &job.UserID, &job.URL, &job.Domain, &job.Status, &job.WorkerType,
            &job.ProgressPercent, &job.ProgressMessage, &job.ResultPath,
            &job.Title, &job.Author, &job.PublishedAt, &job.WordCount, &job.ImageCount,
            &job.ErrorMessage, &job.QueuedAt, &job.StartedAt, &job.CompletedAt,
            &job.CreditsUsed, &job.CreatedAt, &job.UpdatedAt,
        )
        if err != nil {
            return nil, err
        }
        jobs = append(jobs, job)
    }
    return jobs, nil
}

func (r *JobRepository) UpdateStatus(ctx context.Context, id uuid.UUID, status models.JobStatus, message *string) error {
    query := `
        UPDATE jobs
        SET status = $1, progress_message = $2, updated_at = CURRENT_TIMESTAMP
        WHERE id = $3
    `
    _, err := r.db.Exec(ctx, query, status, message, id)
    return err
}

func (r *JobRepository) UpdateProgress(ctx context.Context, id uuid.UUID, percent int, message string) error {
    query := `
        UPDATE jobs
        SET progress_percent = $1, progress_message = $2, updated_at = CURRENT_TIMESTAMP
        WHERE id = $3
    `
    _, err := r.db.Exec(ctx, query, percent, message, id)
    return err
}

func (r *JobRepository) Complete(ctx context.Context, job *models.Job) error {
    query := `
        UPDATE jobs
        SET status = $1, progress_percent = 100,
            result_path = $2, markdown_content = $3,
            title = $4, author = $5, word_count = $6, image_count = $7,
            completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
        WHERE id = $8
    `
    _, err := r.db.Exec(
        ctx, query,
        models.StatusCompleted, job.ResultPath, job.MarkdownContent,
        job.Title, job.Author, job.WordCount, job.ImageCount, job.ID,
    )
    return err
}

func (r *JobRepository) Fail(ctx context.Context, id uuid.UUID, errorMsg string) error {
    query := `
        UPDATE jobs
        SET status = $1, error_message = $2, completed_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = $3
    `
    _, err := r.db.Exec(ctx, query, models.StatusFailed, errorMsg, id)
    return err
}
```

`api/internal/repository/config_repo.go`:
```go
package repository

import (
    "context"
    "fmt"

    "github.com/google/uuid"
    "github.com/jackc/pgx/v5/pgxpool"
    "github.com/Denter-/article-extraction/api/internal/models"
)

type ConfigRepository struct {
    db *pgxpool.Pool
}

func NewConfigRepository(db *pgxpool.Pool) *ConfigRepository {
    return &ConfigRepository{db: db}
}

func (r *ConfigRepository) GetByDomain(ctx context.Context, domain string) (*models.SiteConfig, error) {
    config := &models.SiteConfig{}
    query := `
        SELECT id, domain, config_yaml, requires_browser, learned_by_user_id,
               learned_at, learn_iterations, success_count, failure_count,
               last_used_at, version, notes, created_at, updated_at, avg_extraction_time_ms
        FROM site_configs
        WHERE domain = $1
    `
    err := r.db.QueryRow(ctx, query, domain).Scan(
        &config.ID, &config.Domain, &config.ConfigYAML, &config.RequiresBrowser,
        &config.LearnedByUserID, &config.LearnedAt, &config.LearnIterations,
        &config.SuccessCount, &config.FailureCount, &config.LastUsedAt,
        &config.Version, &config.Notes, &config.CreatedAt, &config.UpdatedAt,
        &config.AvgExtractionTimeMs,
    )
    if err != nil {
        return nil, fmt.Errorf("config not found: %w", err)
    }
    return config, nil
}

func (r *ConfigRepository) Create(ctx context.Context, config *models.SiteConfig) error {
    query := `
        INSERT INTO site_configs (domain, config_yaml, requires_browser, learned_by_user_id, learn_iterations)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, learned_at, created_at, updated_at
    `
    return r.db.QueryRow(
        ctx, query,
        config.Domain, config.ConfigYAML, config.RequiresBrowser, config.LearnedByUserID, config.LearnIterations,
    ).Scan(&config.ID, &config.LearnedAt, &config.CreatedAt, &config.UpdatedAt)
}

func (r *ConfigRepository) UpdateUsageStats(ctx context.Context, domain string, success bool, extractionTimeMs int) error {
    var query string
    if success {
        query = `
            UPDATE site_configs
            SET success_count = success_count + 1,
                last_used_at = CURRENT_TIMESTAMP,
                avg_extraction_time_ms = CASE
                    WHEN avg_extraction_time_ms IS NULL THEN $2
                    ELSE (avg_extraction_time_ms + $2) / 2
                END
            WHERE domain = $1
        `
    } else {
        query = `
            UPDATE site_configs
            SET failure_count = failure_count + 1,
                last_used_at = CURRENT_TIMESTAMP
            WHERE domain = $1
        `
    }
    _, err := r.db.Exec(ctx, query, domain, extractionTimeMs)
    return err
}

func (r *ConfigRepository) ListAll(ctx context.Context, limit int) ([]*models.SiteConfig, error) {
    query := `
        SELECT id, domain, requires_browser, success_count, failure_count,
               last_used_at, learned_at
        FROM site_configs
        ORDER BY last_used_at DESC NULLS LAST
        LIMIT $1
    `
    rows, err := r.db.Query(ctx, query, limit)
    if err != nil {
        return nil, err
    }
    defer rows.Close()

    configs := make([]*models.SiteConfig, 0)
    for rows.Next() {
        config := &models.SiteConfig{}
        err := rows.Scan(
            &config.ID, &config.Domain, &config.RequiresBrowser,
            &config.SuccessCount, &config.FailureCount,
            &config.LastUsedAt, &config.LearnedAt,
        )
        if err != nil {
            return nil, err
        }
        configs = append(configs, config)
    }
    return configs, nil
}
```

**3.3 Testing Phase 3**

✅ **Success Criteria:**
- Models defined with proper validation tags
- Repository methods create/read/update records
- Database operations work correctly
- Test data can be inserted and retrieved

**Test Commands:**
```bash
cd api
go test ./internal/repository/... -v

# Integration test with real database
go test ./tests/integration/... -v
```

---

### Phase 4: Go API - Services & Auth (4 hours)

#### Tasks

**4.1 Auth Service**

`api/internal/service/auth_service.go`:
```go
package service

import (
    "context"
    "crypto/rand"
    "encoding/hex"
    "fmt"
    "time"

    "github.com/golang-jwt/jwt/v5"
    "github.com/google/uuid"
    "golang.org/x/crypto/bcrypt"
    "github.com/Denter-/article-extraction/api/internal/config"
    "github.com/Denter-/article-extraction/api/internal/models"
    "github.com/Denter-/article-extraction/api/internal/repository"
)

type AuthService struct {
    userRepo *repository.UserRepository
    cfg      *config.AuthConfig
}

func NewAuthService(userRepo *repository.UserRepository, cfg *config.AuthConfig) *AuthService {
    return &AuthService{
        userRepo: userRepo,
        cfg:      cfg,
    }
}

func (s *AuthService) Register(ctx context.Context, req *models.CreateUserRequest) (*models.User, error) {
    // Check if user exists
    existing, _ := s.userRepo.GetByEmail(ctx, req.Email)
    if existing != nil {
        return nil, fmt.Errorf("user already exists")
    }

    // Hash password
    passwordHash, err := bcrypt.GenerateFromPassword([]byte(req.Password), s.cfg.BcryptCost)
    if err != nil {
        return nil, fmt.Errorf("failed to hash password: %w", err)
    }

    // Generate API key
    apiKey := generateAPIKey()

    user := &models.User{
        Email:        req.Email,
        PasswordHash: string(passwordHash),
        Tier:         models.TierFree,
        Credits:      10, // Free tier starts with 10 credits
        APIKey:       &apiKey,
        IsActive:     true,
    }

    if err := s.userRepo.Create(ctx, user); err != nil {
        return nil, fmt.Errorf("failed to create user: %w", err)
    }

    return user, nil
}

func (s *AuthService) Login(ctx context.Context, req *models.LoginRequest) (*models.LoginResponse, error) {
    user, err := s.userRepo.GetByEmail(ctx, req.Email)
    if err != nil {
        return nil, fmt.Errorf("invalid credentials")
    }

    // Verify password
    if err := bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(req.Password)); err != nil {
        return nil, fmt.Errorf("invalid credentials")
    }

    // Update last login
    s.userRepo.UpdateLastLogin(ctx, user.ID)

    // Generate JWT
    token, err := s.generateJWT(user)
    if err != nil {
        return nil, fmt.Errorf("failed to generate token: %w", err)
    }

    return &models.LoginResponse{
        Token: token,
        User:  *user,
    }, nil
}

func (s *AuthService) ValidateToken(tokenString string) (*models.User, error) {
    token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
        if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
            return nil, fmt.Errorf("unexpected signing method")
        }
        return []byte(s.cfg.JWTSecret), nil
    })

    if err != nil || !token.Valid {
        return nil, fmt.Errorf("invalid token")
    }

    claims, ok := token.Claims.(jwt.MapClaims)
    if !ok {
        return nil, fmt.Errorf("invalid token claims")
    }

    userIDStr, ok := claims["user_id"].(string)
    if !ok {
        return nil, fmt.Errorf("invalid user_id in token")
    }

    userID, err := uuid.Parse(userIDStr)
    if err != nil {
        return nil, fmt.Errorf("invalid user_id format")
    }

    user, err := s.userRepo.GetByID(context.Background(), userID)
    if err != nil {
        return nil, fmt.Errorf("user not found")
    }

    return user, nil
}

func (s *AuthService) ValidateAPIKey(ctx context.Context, apiKey string) (*models.User, error) {
    user, err := s.userRepo.GetByAPIKey(ctx, apiKey)
    if err != nil {
        return nil, fmt.Errorf("invalid API key")
    }
    return user, nil
}

func (s *AuthService) generateJWT(user *models.User) (string, error) {
    claims := jwt.MapClaims{
        "user_id": user.ID.String(),
        "email":   user.Email,
        "tier":    user.Tier,
        "exp":     time.Now().Add(time.Hour * time.Duration(s.cfg.JWTExpiryHours)).Unix(),
        "iat":     time.Now().Unix(),
    }

    token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
    return token.SignedString([]byte(s.cfg.JWTSecret))
}

func generateAPIKey() string {
    b := make([]byte, 32)
    rand.Read(b)
    return hex.EncodeToString(b)
}
```

**4.2 Job Service**

`api/internal/service/job_service.go`:
```go
package service

import (
    "context"
    "fmt"
    "net/url"
    "strings"

    "github.com/google/uuid"
    "github.com/Denter-/article-extraction/api/internal/models"
    "github.com/Denter-/article-extraction/api/internal/repository"
)

type JobService struct {
    jobRepo    *repository.JobRepository
    configRepo *repository.ConfigRepository
    userRepo   *repository.UserRepository
    queueSvc   *QueueService
}

func NewJobService(
    jobRepo *repository.JobRepository,
    configRepo *repository.ConfigRepository,
    userRepo *repository.UserRepository,
    queueSvc *QueueService,
) *JobService {
    return &JobService{
        jobRepo:    jobRepo,
        configRepo: configRepo,
        userRepo:   userRepo,
        queueSvc:   queueSvc,
    }
}

func (s *JobService) CreateJob(ctx context.Context, userID uuid.UUID, req *models.CreateJobRequest) (*models.Job, error) {
    // Check user credits
    user, err := s.userRepo.GetByID(ctx, userID)
    if err != nil {
        return nil, fmt.Errorf("user not found: %w", err)
    }

    if user.Credits < 1 {
        return nil, fmt.Errorf("insufficient credits")
    }

    // Parse domain
    domain, err := extractDomain(req.URL)
    if err != nil {
        return nil, fmt.Errorf("invalid URL: %w", err)
    }

    // Create job
    job := &models.Job{
        UserID:      userID,
        URL:         req.URL,
        Domain:      domain,
        Status:      models.StatusQueued,
        CreditsUsed: 1,
    }

    if err := s.jobRepo.Create(ctx, job); err != nil {
        return nil, fmt.Errorf("failed to create job: %w", err)
    }

    // Deduct credits
    newCredits := user.Credits - 1
    if err := s.userRepo.UpdateCredits(ctx, userID, newCredits); err != nil {
        return nil, fmt.Errorf("failed to update credits: %w", err)
    }

    // Queue job for processing
    if err := s.queueSvc.EnqueueJob(ctx, job); err != nil {
        return nil, fmt.Errorf("failed to queue job: %w", err)
    }

    return job, nil
}

func (s *JobService) CreateBatchJobs(ctx context.Context, userID uuid.UUID, req *models.CreateBatchJobRequest) ([]*models.Job, error) {
    // Check user credits
    user, err := s.userRepo.GetByID(ctx, userID)
    if err != nil {
        return nil, fmt.Errorf("user not found: %w", err)
    }

    requiredCredits := len(req.URLs)
    if user.Credits < requiredCredits {
        return nil, fmt.Errorf("insufficient credits: need %d, have %d", requiredCredits, user.Credits)
    }

    // Create all jobs
    jobs := make([]*models.Job, 0, len(req.URLs))
    for _, urlStr := range req.URLs {
        domain, err := extractDomain(urlStr)
        if err != nil {
            continue // Skip invalid URLs
        }

        job := &models.Job{
            UserID:      userID,
            URL:         urlStr,
            Domain:      domain,
            Status:      models.StatusQueued,
            CreditsUsed: 1,
        }

        if err := s.jobRepo.Create(ctx, job); err != nil {
            continue // Skip failed creations
        }

        jobs = append(jobs, job)
    }

    // Deduct credits
    newCredits := user.Credits - len(jobs)
    if err := s.userRepo.UpdateCredits(ctx, userID, newCredits); err != nil {
        return nil, fmt.Errorf("failed to update credits: %w", err)
    }

    // Queue all jobs
    for _, job := range jobs {
        s.queueSvc.EnqueueJob(ctx, job)
    }

    return jobs, nil
}

func (s *JobService) GetJob(ctx context.Context, jobID uuid.UUID, userID uuid.UUID) (*models.Job, error) {
    job, err := s.jobRepo.GetByID(ctx, jobID)
    if err != nil {
        return nil, fmt.Errorf("job not found: %w", err)
    }

    // Verify ownership
    if job.UserID != userID {
        return nil, fmt.Errorf("unauthorized")
    }

    return job, nil
}

func (s *JobService) ListUserJobs(ctx context.Context, userID uuid.UUID, limit int) ([]*models.Job, error) {
    if limit <= 0 || limit > 100 {
        limit = 20
    }
    return s.jobRepo.GetByUserID(ctx, userID, limit)
}

func extractDomain(urlStr string) (string, error) {
    parsedURL, err := url.Parse(urlStr)
    if err != nil {
        return "", err
    }

    host := parsedURL.Hostname()
    // Remove www. prefix
    host = strings.TrimPrefix(host, "www.")

    return host, nil
}
```

**4.3 Queue Service (Redis-based)**

`api/internal/service/queue_service.go`:
```go
package service

import (
    "context"
    "encoding/json"
    "fmt"

    "github.com/hibiken/asynq"
    "github.com/Denter-/article-extraction/api/internal/models"
)

const (
    TypeExtractionJob = "extraction:job"
)

type QueueService struct {
    client *asynq.Client
}

func NewQueueService(redisAddr string) *QueueService {
    client := asynq.NewClient(asynq.RedisClientOpt{Addr: redisAddr})
    return &QueueService{client: client}
}

func (s *QueueService) EnqueueJob(ctx context.Context, job *models.Job) error {
    payload, err := json.Marshal(job)
    if err != nil {
        return fmt.Errorf("failed to marshal job: %w", err)
    }

    task := asynq.NewTask(TypeExtractionJob, payload)

    // Enqueue with options
    _, err = s.client.EnqueueContext(ctx, task)
    if err != nil {
        return fmt.Errorf("failed to enqueue task: %w", err)
    }

    return nil
}

func (s *QueueService) Close() error {
    return s.client.Close()
}
```

**4.4 Testing Phase 4**

✅ **Success Criteria:**
- User registration creates user with hashed password
- Login returns valid JWT token
- Token validation works correctly
- API key authentication works
- Jobs can be created and queued
- Credits are deducted correctly

**Test Commands:**
```bash
cd api
go test ./internal/service/... -v
```

---

### Phase 5: Go API - HTTP Handlers & Middleware (4 hours)

#### Tasks

**5.1 Middleware**

`api/internal/middleware/auth.go`:
```go
package middleware

import (
    "strings"

    "github.com/gofiber/fiber/v2"
    "github.com/Denter-/article-extraction/api/internal/service"
)

func AuthRequired(authSvc *service.AuthService) fiber.Handler {
    return func(c *fiber.Ctx) error {
        // Try Bearer token first
        authHeader := c.Get("Authorization")
        if authHeader != "" {
            parts := strings.Split(authHeader, " ")
            if len(parts) == 2 && parts[0] == "Bearer" {
                user, err := authSvc.ValidateToken(parts[1])
                if err == nil {
                    c.Locals("user", user)
                    return c.Next()
                }
            }
        }

        // Try API key
        apiKey := c.Get("X-API-Key")
        if apiKey != "" {
            user, err := authSvc.ValidateAPIKey(c.Context(), apiKey)
            if err == nil {
                c.Locals("user", user)
                return c.Next()
            }
        }

        return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
            "error": "Unauthorized",
        })
    }
}
```

`api/internal/middleware/ratelimit.go`:
```go
package middleware

import (
    "context"
    "fmt"
    "time"

    "github.com/gofiber/fiber/v2"
    "github.com/redis/go-redis/v9"
    "github.com/Denter-/article-extraction/api/internal/config"
    "github.com/Denter-/article-extraction/api/internal/models"
)

func RateLimit(rdb *redis.Client, cfg *config.RateLimitConfig) fiber.Handler {
    return func(c *fiber.Ctx) error {
        user, ok := c.Locals("user").(*models.User)
        if !ok {
            return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
                "error": "Unauthorized",
            })
        }

        // Determine rate limit based on tier
        var limit int
        switch user.Tier {
        case models.TierFree:
            limit = cfg.Free
        case models.TierPro:
            limit = cfg.Pro
        default:
            limit = cfg.Pro
        }

        key := fmt.Sprintf("ratelimit:%s:%s", user.ID, time.Now().Format("2006-01-02-15"))
        ctx := context.Background()

        // Increment counter
        count, err := rdb.Incr(ctx, key).Result()
        if err != nil {
            // Don't block on Redis errors
            return c.Next()
        }

        // Set expiry on first request
        if count == 1 {
            rdb.Expire(ctx, key, cfg.Window)
        }

        if count > int64(limit) {
            return c.Status(fiber.StatusTooManyRequests).JSON(fiber.Map{
                "error":       "Rate limit exceeded",
                "limit":       limit,
                "window":      cfg.Window.String(),
                "retry_after": cfg.Window.Seconds(),
            })
        }

        // Add rate limit headers
        c.Set("X-RateLimit-Limit", fmt.Sprintf("%d", limit))
        c.Set("X-RateLimit-Remaining", fmt.Sprintf("%d", limit-int(count)))

        return c.Next()
    }
}
```

`api/internal/middleware/logger.go`:
```go
package middleware

import (
    "time"

    "github.com/gofiber/fiber/v2"
    "github.com/rs/zerolog/log"
)

func Logger() fiber.Handler {
    return func(c *fiber.Ctx) error {
        start := time.Now()

        err := c.Next()

        log.Info().
            Str("method", c.Method()).
            Str("path", c.Path()).
            Int("status", c.Response().StatusCode()).
            Dur("latency", time.Since(start)).
            Str("ip", c.IP()).
            Msg("Request")

        return err
    }
}
```

**5.2 HTTP Handlers**

`api/internal/handlers/auth.go`:
```go
package handlers

import (
    "github.com/go-playground/validator/v10"
    "github.com/gofiber/fiber/v2"
    "github.com/Denter-/article-extraction/api/internal/models"
    "github.com/Denter-/article-extraction/api/internal/service"
)

type AuthHandler struct {
    authSvc   *service.AuthService
    validator *validator.Validate
}

func NewAuthHandler(authSvc *service.AuthService) *AuthHandler {
    return &AuthHandler{
        authSvc:   authSvc,
        validator: validator.New(),
    }
}

func (h *AuthHandler) Register(c *fiber.Ctx) error {
    var req models.CreateUserRequest
    if err := c.BodyParser(&req); err != nil {
        return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
            "error": "Invalid request body",
        })
    }

    if err := h.validator.Struct(&req); err != nil {
        return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
            "error": err.Error(),
        })
    }

    user, err := h.authSvc.Register(c.Context(), &req)
    if err != nil {
        return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
            "error": err.Error(),
        })
    }

    return c.Status(fiber.StatusCreated).JSON(fiber.Map{
        "user": user,
    })
}

func (h *AuthHandler) Login(c *fiber.Ctx) error {
    var req models.LoginRequest
    if err := c.BodyParser(&req); err != nil {
        return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
            "error": "Invalid request body",
        })
    }

    if err := h.validator.Struct(&req); err != nil {
        return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
            "error": err.Error(),
        })
    }

    response, err := h.authSvc.Login(c.Context(), &req)
    if err != nil {
        return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
            "error": err.Error(),
        })
    }

    return c.JSON(response)
}

func (h *AuthHandler) Me(c *fiber.Ctx) error {
    user, ok := c.Locals("user").(*models.User)
    if !ok {
        return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
            "error": "Unauthorized",
        })
    }

    return c.JSON(fiber.Map{
        "user": user,
    })
}
```

`api/internal/handlers/extract.go`:
```go
package handlers

import (
    "github.com/go-playground/validator/v10"
    "github.com/gofiber/fiber/v2"
    "github.com/Denter-/article-extraction/api/internal/models"
    "github.com/Denter-/article-extraction/api/internal/service"
)

type ExtractHandler struct {
    jobSvc    *service.JobService
    validator *validator.Validate
}

func NewExtractHandler(jobSvc *service.JobService) *ExtractHandler {
    return &ExtractHandler{
        jobSvc:    jobSvc,
        validator: validator.New(),
    }
}

func (h *ExtractHandler) ExtractSingle(c *fiber.Ctx) error {
    user, ok := c.Locals("user").(*models.User)
    if !ok {
        return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
            "error": "Unauthorized",
        })
    }

    var req models.CreateJobRequest
    if err := c.BodyParser(&req); err != nil {
        return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
            "error": "Invalid request body",
        })
    }

    if err := h.validator.Struct(&req); err != nil {
        return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
            "error": err.Error(),
        })
    }

    job, err := h.jobSvc.CreateJob(c.Context(), user.ID, &req)
    if err != nil {
        return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
            "error": err.Error(),
        })
    }

    return c.Status(fiber.StatusAccepted).JSON(fiber.Map{
        "job": job,
        "message": "Job queued for processing",
    })
}

func (h *ExtractHandler) ExtractBatch(c *fiber.Ctx) error {
    user, ok := c.Locals("user").(*models.User)
    if !ok {
        return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
            "error": "Unauthorized",
        })
    }

    var req models.CreateBatchJobRequest
    if err := c.BodyParser(&req); err != nil {
        return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
            "error": "Invalid request body",
        })
    }

    if err := h.validator.Struct(&req); err != nil {
        return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
            "error": err.Error(),
        })
    }

    jobs, err := h.jobSvc.CreateBatchJobs(c.Context(), user.ID, &req)
    if err != nil {
        return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
            "error": err.Error(),
        })
    }

    return c.Status(fiber.StatusAccepted).JSON(fiber.Map{
        "jobs": jobs,
        "count": len(jobs),
        "message": "Batch jobs queued for processing",
    })
}
```

`api/internal/handlers/jobs.go`:
```go
package handlers

import (
    "github.com/gofiber/fiber/v2"
    "github.com/google/uuid"
    "github.com/Denter-/article-extraction/api/internal/models"
    "github.com/Denter-/article-extraction/api/internal/service"
)

type JobHandler struct {
    jobSvc *service.JobService
}

func NewJobHandler(jobSvc *service.JobService) *JobHandler {
    return &JobHandler{
        jobSvc: jobSvc,
    }
}

func (h *JobHandler) GetJob(c *fiber.Ctx) error {
    user, ok := c.Locals("user").(*models.User)
    if !ok {
        return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
            "error": "Unauthorized",
        })
    }

    jobIDStr := c.Params("id")
    jobID, err := uuid.Parse(jobIDStr)
    if err != nil {
        return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
            "error": "Invalid job ID",
        })
    }

    job, err := h.jobSvc.GetJob(c.Context(), jobID, user.ID)
    if err != nil {
        return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
            "error": err.Error(),
        })
    }

    return c.JSON(fiber.Map{
        "job": job,
    })
}

func (h *JobHandler) ListJobs(c *fiber.Ctx) error {
    user, ok := c.Locals("user").(*models.User)
    if !ok {
        return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
            "error": "Unauthorized",
        })
    }

    limit := c.QueryInt("limit", 20)
    jobs, err := h.jobSvc.ListUserJobs(c.Context(), user.ID, limit)
    if err != nil {
        return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
            "error": err.Error(),
        })
    }

    return c.JSON(fiber.Map{
        "jobs": jobs,
        "count": len(jobs),
    })
}
```

**5.3 Main API Server**

`api/cmd/api/main.go`:
```go
package main

import (
    "fmt"
    "log"
    "os"

    "github.com/gofiber/fiber/v2"
    "github.com/gofiber/fiber/v2/middleware/cors"
    "github.com/gofiber/fiber/v2/middleware/recover"
    "github.com/rs/zerolog"
    zlog "github.com/rs/zerolog/log"

    "github.com/Denter-/article-extraction/api/internal/config"
    "github.com/Denter-/article-extraction/api/internal/database"
    "github.com/Denter-/article-extraction/api/internal/handlers"
    "github.com/Denter-/article-extraction/api/internal/middleware"
    "github.com/Denter-/article-extraction/api/internal/repository"
    "github.com/Denter-/article-extraction/api/internal/service"
)

func main() {
    // Setup logging
    zerolog.TimeFieldFormat = zerolog.TimeFormatUnix
    zlog.Logger = zlog.Output(zerolog.ConsoleWriter{Out: os.Stderr})

    // Load configuration
    cfg, err := config.Load()
    if err != nil {
        log.Fatalf("Failed to load config: %v", err)
    }

    // Connect to PostgreSQL
    db, err := database.NewPostgresPool(&cfg.Database)
    if err != nil {
        log.Fatalf("Failed to connect to database: %v", err)
    }
    defer db.Close()
    zlog.Info().Msg("Connected to PostgreSQL")

    // Connect to Redis
    rdb, err := database.NewRedisClient(&cfg.Redis)
    if err != nil {
        log.Fatalf("Failed to connect to Redis: %v", err)
    }
    defer rdb.Close()
    zlog.Info().Msg("Connected to Redis")

    // Initialize repositories
    userRepo := repository.NewUserRepository(db)
    jobRepo := repository.NewJobRepository(db)
    configRepo := repository.NewConfigRepository(db)

    // Initialize services
    queueSvc := service.NewQueueService(fmt.Sprintf("%s:%d", cfg.Redis.Host, cfg.Redis.Port))
    defer queueSvc.Close()

    authSvc := service.NewAuthService(userRepo, &cfg.Auth)
    jobSvc := service.NewJobService(jobRepo, configRepo, userRepo, queueSvc)

    // Initialize handlers
    authHandler := handlers.NewAuthHandler(authSvc)
    extractHandler := handlers.NewExtractHandler(jobSvc)
    jobHandler := handlers.NewJobHandler(jobSvc)

    // Create Fiber app
    app := fiber.New(fiber.Config{
        ErrorHandler: customErrorHandler,
        AppName:      "Article Extraction API",
    })

    // Global middleware
    app.Use(recover.New())
    app.Use(cors.New())
    app.Use(middleware.Logger())

    // Public routes
    app.Get("/health", func(c *fiber.Ctx) error {
        return c.JSON(fiber.Map{
            "status": "healthy",
            "service": "article-extraction-api",
        })
    })

    // Auth routes
    auth := app.Group("/api/v1/auth")
    auth.Post("/register", authHandler.Register)
    auth.Post("/login", authHandler.Login)
    auth.Get("/me", middleware.AuthRequired(authSvc), authHandler.Me)

    // Protected routes
    api := app.Group("/api/v1")
    api.Use(middleware.AuthRequired(authSvc))
    api.Use(middleware.RateLimit(rdb, &cfg.RateLimit))

    // Extract routes
    api.Post("/extract/single", extractHandler.ExtractSingle)
    api.Post("/extract/batch", extractHandler.ExtractBatch)

    // Job routes
    api.Get("/jobs/:id", jobHandler.GetJob)
    api.Get("/jobs", jobHandler.ListJobs)

    // Start server
    addr := fmt.Sprintf("%s:%s", cfg.Server.Host, cfg.Server.Port)
    zlog.Info().Msgf("Starting server on %s", addr)
    if err := app.Listen(addr); err != nil {
        log.Fatalf("Failed to start server: %v", err)
    }
}

func customErrorHandler(c *fiber.Ctx, err error) error {
    code := fiber.StatusInternalServerError
    if e, ok := err.(*fiber.Error); ok {
        code = e.Code
    }

    return c.Status(code).JSON(fiber.Map{
        "error": err.Error(),
    })
}
```

**5.4 Testing Phase 5**

✅ **Success Criteria:**
- API server starts successfully
- Health endpoint returns 200
- Registration creates user and returns 201
- Login returns JWT token
- Protected endpoints require authentication
- Rate limiting works
- Invalid requests return appropriate errors

**Test Script:** `api/tests/api_test.sh`:
```bash
#!/bin/bash

BASE_URL="http://localhost:8080"

echo "Testing API..."

# Health check
echo "1. Health check..."
curl -s $BASE_URL/health | jq

# Register
echo "2. Register new user..."
REGISTER_RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}')
echo $REGISTER_RESPONSE | jq

# Login
echo "3. Login..."
LOGIN_RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}')
echo $LOGIN_RESPONSE | jq

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.token')

# Get user info
echo "4. Get user info..."
curl -s $BASE_URL/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN" | jq

# Create extraction job
echo "5. Create extraction job..."
curl -s -X POST $BASE_URL/api/v1/extract/single \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.forentrepreneurs.com/startup-killer/"}' | jq

# List jobs
echo "6. List jobs..."
curl -s $BASE_URL/api/v1/jobs \
  -H "Authorization: Bearer $TOKEN" | jq

echo "API tests complete!"
```

---

### Phase 6: Go Worker - Fast Path (6 hours)

(Continuing in next section due to length...)

This is getting quite large. Would you like me to:
1. Continue with the remaining phases (Go Worker, Python Worker, Local dev setup, Testing)?
2. Package this as a complete document and create additional files for implementation details?
3. Focus on specific sections you want to drill into?

The document is about halfway complete - we still need to cover:
- Phase 6: Go Worker implementation
- Phase 7: Python AI Worker service
- Phase 8: Local development scripts
- Phase 9: Testing strategy
- Phase 10: Cloud deployment

What would be most useful for you?

