# Workers Documentation

**Complete documentation for Go and Python workers**

---

## 🎯 Overview

The system uses two types of workers to handle different extraction scenarios:

- **Go Worker** - Fast path for simple sites (no JavaScript)
- **Python AI Worker** - Complex sites requiring browser automation and AI learning

---

## 🏗️ Architecture Overview

### **Worker Assignment Logic**
```mermaid
flowchart TD
    A[Article URL] --> B[API Server]
    B --> C[Job Queue]
    C --> D[Worker Selection]
    D --> E{Site Config Exists?}
    E -->|Yes| F[Check Config]
    E -->|No| G[Python AI Worker]
    F --> H{Requires Browser?}
    H -->|No| I[Go Worker<br/>Fast Path]
    H -->|Yes| G[Python AI Worker<br/>AI + Browser]
    I --> J[Extract Content]
    G --> K[Learn Site + Extract]
    J --> L[Save Result]
    K --> L
```

### **Job Processing Flow**
```mermaid
sequenceDiagram
    participant Queue as Redis Queue
    participant Worker as Worker
    participant Config as Site Config
    participant AI as AI Services
    participant DB as Database
    participant Storage as File Storage

    Queue->>Worker: Job Queued
    Worker->>Worker: Status: processing
    Worker->>Config: Check Site Config
    Config-->>Worker: Config or None
    
    alt Config Exists
        Worker->>Worker: Extract Content (HTML parsing)
    else No Config
        Worker->>AI: Learn Site Structure
        AI-->>Worker: Site Config
        Worker->>Worker: Extract Content (browser automation)
    end
    
    Worker->>AI: Generate Image Descriptions
    AI-->>Worker: Descriptions
    Worker->>Worker: Convert to Markdown
    Worker->>DB: Save Result
    Worker->>Storage: Save File
    Worker->>Worker: Status: completed
```

---

## 🚀 Go Worker (Fast Path)

### **Purpose**
- Handle simple sites with static HTML
- Fast extraction without browser overhead
- Basic content cleaning and markdown conversion

### **Technology Stack**
- **Go 1.21+** - Programming language
- **goquery** - HTML parsing (jQuery-like)
- **asynq** - Job queue processing
- **pgx** - PostgreSQL driver
- **go-redis** - Redis client

### **Project Structure**
```
worker-go/
├── cmd/worker/main.go          # Worker entry point
├── internal/
│   ├── config/                # Configuration
│   │   └── config.go
│   ├── extractor/              # Extraction logic
│   │   ├── extractor.go
│   │   ├── fetcher.go
│   │   └── default_exclusions.go
│   ├── gemini/                 # AI integration
│   │   └── client.go
│   ├── repository/             # Database access
│   │   └── job_repo.go
│   └── worker/                 # Job processing
│       └── handler.go
└── tests/                      # Test files
```

### **Main Worker Loop**
```go
// cmd/worker/main.go
func main() {
    // Setup logging
    zlog.Info().Msg("🚀 Starting Article Extraction Worker (Go Fast Path)...")
    
    // Load configuration
    cfg, err := config.Load()
    
    // Connect to database
    db, err := repository.NewPostgresPool(cfg.Database.URL)
    
    // Initialize repositories
    jobRepo := repository.NewJobRepository(db)
    configRepo := repository.NewConfigRepository(db)
    
    // Initialize Gemini client
    geminiClient, err := gemini.NewClient(cfg.Gemini.APIKey)
    
    // Initialize extractor
    extractorInstance := extractor.New(geminiClient, cfg.Storage.Path, "config/sites")
    
    // Create worker handler
    handler := worker.NewHandler(jobRepo, configRepo, extractorInstance)
    
    // Create asynq server
    srv := asynq.NewServer(
        asynq.RedisClientOpt{Addr: redisAddr},
        asynq.Config{
            Concurrency: cfg.Queue.Concurrency,
            Queues: map[string]int{
                "critical": 6,
                "default":  3,
                "low":      1,
            },
        },
    )
    
    // Register handler
    mux := asynq.NewServeMux()
    mux.HandleFunc(worker.TypeExtractionJob, handler.HandleExtractionJob)
    
    // Start worker
    srv.Run(mux)
}
```

### **Job Handler**
```go
// internal/worker/handler.go
func (h *Handler) HandleExtractionJob(ctx context.Context, t *asynq.Task) error {
    var job models.Job
    if err := json.Unmarshal(t.Payload(), &job); err != nil {
        return fmt.Errorf("unmarshal job: %w", err)
    }
    
    // Update job status
    h.jobRepo.UpdateStatus(ctx, job.ID, models.StatusProcessing, nil)
    
    // Get site configuration
    config, err := h.configRepo.GetByDomain(ctx, job.Domain)
    if err != nil {
        // No config exists - delegate to Python worker
        return h.delegateToPythonWorker(ctx, &job)
    }
    
    // Extract using Go worker
    result, err := h.extractor.ExtractArticle(ctx, job.URL, config)
    if err != nil {
        return h.handleExtractionError(ctx, &job, err)
    }
    
    // Update job with results
    h.jobRepo.Complete(ctx, &job, result)
    
    return nil
}
```

### **Content Extraction**
```go
// internal/extractor/extractor.go
func (e *Extractor) ExtractArticle(ctx context.Context, url string, config *models.SiteConfig) (*ExtractionResult, error) {
    // Fetch HTML content
    html, err := e.fetcher.FetchHTML(ctx, url)
    if err != nil {
        return nil, fmt.Errorf("fetch HTML: %w", err)
    }
    
    // Parse HTML
    doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
    if err != nil {
        return nil, fmt.Errorf("parse HTML: %w", err)
    }
    
    // Extract content using site config
    content, err := e.extractContent(doc, config)
    if err != nil {
        return nil, fmt.Errorf("extract content: %w", err)
    }
    
    // Extract metadata
    metadata := e.extractMetadata(doc, config)
    
    // Generate image descriptions (if enabled)
    if e.geminiClient != nil {
        descriptions, err := e.generateImageDescriptions(ctx, content)
        if err != nil {
            log.Printf("Warning: Failed to generate image descriptions: %v", err)
        } else {
            content = e.integrateImageDescriptions(content, descriptions)
        }
    }
    
    // Convert to markdown
    markdown := e.convertToMarkdown(content, metadata)
    
    return &ExtractionResult{
        Markdown: markdown,
        Metadata: metadata,
        WordCount: len(strings.Fields(markdown)),
        ImageCount: len(descriptions),
    }, nil
}
```

---

## 🐍 Python AI Worker

### **Purpose**
- Handle complex sites requiring browser automation
- AI-powered site learning for new domains
- Advanced content processing with Gemini integration

### **Technology Stack**
- **Python 3.8+** - Programming language
- **FastAPI** - Web framework for API endpoints
- **Playwright** - Browser automation
- **BeautifulSoup** - HTML parsing
- **Google Gemini** - AI for learning and descriptions

### **Project Structure**
```
worker-python/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── ai_worker.py            # AI worker logic
│   └── database.py             # Database connection
├── config/
│   └── settings.py             # Configuration
├── requirements.txt            # Python dependencies
└── tests/                      # Test files
```

### **FastAPI Application**
```python
# app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn

from config.settings import settings
from app.database import Database
from app.ai_worker import AIWorker

app = FastAPI(
    title="Article Extraction AI Worker",
    description="AI-powered site learning and complex article extraction",
    version="1.0.0"
)

# Initialize database and worker
db = Database(settings.database_url)
ai_worker = None

@app.on_event("startup")
async def startup_event():
    global ai_worker
    db.connect()
    ai_worker = AIWorker(db)
    logger.info("AI Worker service started")

@app.post("/learn")
async def learn_site(request: LearnRequest):
    """Learn extraction rules for a new site using AI"""
    try:
        result = ai_worker.process_learning_job(request.job_id, request.url)
        
        if result['success']:
            return LearnResponse(
                success=True,
                message="Site learned and article extracted successfully",
                config=result.get('config')
            )
        else:
            return LearnResponse(
                success=False,
                message="Failed to learn site",
                error=result.get('error')
            )
    
    except Exception as e:
        logger.error(f"Error processing learning request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract-browser")
async def extract_with_browser(request: LearnRequest):
    """Extract article using browser for JavaScript-rendered sites"""
    try:
        result = ai_worker.process_learning_job(request.job_id, request.url)
        
        return LearnResponse(
            success=result['success'],
            message="Browser extraction completed" if result['success'] else "Extraction failed",
            error=result.get('error')
        )
    
    except Exception as e:
        logger.error(f"Error in browser extraction: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### **AI Worker Logic**
```python
# app/ai_worker.py
class AIWorker:
    def __init__(self, db: Database):
        self.db = db
        self.site_registry = SiteRegistry(use_gemini=True)
        self.extraction_engine = ExtractionEngine()
    
    def process_learning_job(self, job_id: str, url: str) -> dict:
        """Process a learning job - learn site and extract article"""
        try:
            # Get job from database
            job = self.db.get_job(job_id)
            if not job:
                return {'success': False, 'error': 'Job not found'}
            
            # Update job status
            self.db.update_job_status(job_id, 'learning', 'Learning site structure...')
            
            # Learn site configuration
            success, config, error = self.site_registry.learn_site(url)
            
            if not success:
                self.db.update_job_status(job_id, 'failed', f'Learning failed: {error}')
                return {'success': False, 'error': error}
            
            # Extract article using learned config
            self.db.update_job_status(job_id, 'extracting', 'Extracting article content...')
            
            result = self.extraction_engine.extract_article(url, config)
            
            if result['success']:
                # Save result to database
                self.db.complete_job(job_id, result)
                return {'success': True, 'config': config}
            else:
                self.db.update_job_status(job_id, 'failed', f'Extraction failed: {result["error"]}')
                return {'success': False, 'error': result['error']}
                
        except Exception as e:
            logger.error(f"Error in AI worker: {e}", exc_info=True)
            self.db.update_job_status(job_id, 'failed', f'Worker error: {str(e)}')
            return {'success': False, 'error': str(e)}
```

---

## 🔄 Worker Coordination

### **Job Delegation Logic**
```go
// Go worker delegates to Python worker
func (h *Handler) delegateToPythonWorker(ctx context.Context, job *models.Job) error {
    // Update job status
    h.jobRepo.UpdateStatus(ctx, job.ID, models.StatusLearning, nil)
    
    // Call Python worker API
    client := &http.Client{Timeout: 30 * time.Second}
    
    payload := map[string]string{
        "job_id": job.ID.String(),
        "url":    job.URL,
    }
    
    jsonData, _ := json.Marshal(payload)
    
    resp, err := client.Post(
        "http://localhost:8081/learn",
        "application/json",
        bytes.NewBuffer(jsonData),
    )
    
    if err != nil {
        return h.handleDelegationError(ctx, job, err)
    }
    defer resp.Body.Close()
    
    if resp.StatusCode != 200 {
        return h.handleDelegationError(ctx, job, fmt.Errorf("Python worker error: %d", resp.StatusCode))
    }
    
    return nil
}
```

### **Python Worker Integration**
```python
# app/ai_worker.py
def process_learning_job(self, job_id: str, url: str) -> dict:
    """Process learning job with full AI integration"""
    
    # Check if site requires browser
    requires_browser = self.detect_javascript_requirements(url)
    
    if requires_browser:
        # Use Playwright for JavaScript-heavy sites
        return self.extract_with_browser(job_id, url)
    else:
        # Use standard extraction
        return self.extract_with_requests(job_id, url)

def extract_with_browser(self, job_id: str, url: str) -> dict:
    """Extract using browser automation"""
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        try:
            # Navigate to page
            page.goto(url, wait_until='networkidle')
            
            # Wait for content to load
            page.wait_for_selector('body', timeout=10000)
            
            # Get HTML content
            html = page.content()
            
            # Learn site configuration
            success, config, error = self.site_registry.learn_site_from_html(html, url)
            
            if success:
                # Extract content using learned config
                result = self.extraction_engine.extract_from_html(html, config)
                return {'success': True, 'result': result, 'config': config}
            else:
                return {'success': False, 'error': error}
                
        finally:
            browser.close()
```

---

## 🧠 AI Integration

### **Site Learning Process**
```python
# src/site_registry.py
def learn_site(self, url: str, max_iterations: int = 3) -> tuple[bool, dict, str]:
    """Learn extraction rules for a new site using AI"""
    
    # Download page content
    html_content = self.fetch_page_content(url)
    
    # Check if browser is required
    requires_browser = self.detect_javascript_requirements(html_content)
    
    # Learn extraction rules
    for iteration in range(max_iterations):
        if iteration == 0:
            # First iteration: ask AI for initial config
            config = self._ask_gemini_for_config(html_content, url)
        else:
            # Subsequent iterations: improve based on feedback
            config = self._ask_gemini_for_better_config(html_content, url, old_config, feedback)
        
        # Test extraction with current config
        extracted_html = self.extract_with_config(html_content, config)
        
        if not extracted_html:
            feedback = "No content extracted - selector too strict"
            continue
        
        # Validate extraction quality
        is_valid, feedback, filter_changes = self._validate_and_suggest_filters(
            html_content, extracted_html, config
        )
        
        if is_valid:
            # Learning successful
            config['requires_browser'] = requires_browser
            self.save_config(domain, config)
            return True, config, None
        else:
            # Apply filter adjustments
            if filter_changes:
                config = self._apply_filter_changes(config, filter_changes)
    
    return False, None, f"Failed to learn valid rules after {max_iterations} attempts"
```

### **Image Description Generation**
```python
# src/article_extractor.py
def generate_image_description(self, image_url: str) -> str:
    """Generate AI description for an image"""
    if not self.gemini_client:
        return "Image description not available"
    
    try:
        # Download image
        image_data = self.download_image(image_url)
        
        # Generate description using Gemini Vision
        description = self.gemini_client.generate_image_description(image_data)
        
        return description
    except Exception as e:
        logger.warning(f"Failed to generate image description: {e}")
        return "Image description generation failed"
```

---

## 📊 Performance Optimization

### **Go Worker Optimization**
```go
// Concurrent processing
func (h *Handler) HandleExtractionJob(ctx context.Context, t *asynq.Task) error {
    // Process job in goroutine for non-blocking operation
    go func() {
        defer func() {
            if r := recover(); r != nil {
                log.Printf("Worker panic recovered: %v", r)
            }
        }()
        
        // Process extraction
        result, err := h.extractor.ExtractArticle(ctx, job.URL, config)
        // Handle result...
    }()
    
    return nil
}

// Connection pooling
func NewPostgresPool(url string) (*pgxpool.Pool, error) {
    config, err := pgxpool.ParseConfig(url)
    if err != nil {
        return nil, err
    }
    
    config.MaxConns = 25
    config.MinConns = 5
    config.MaxConnLifetime = time.Hour
    config.MaxConnIdleTime = 30 * time.Minute
    
    return pgxpool.NewWithConfig(context.Background(), config)
}
```

### **Python Worker Optimization**
```python
# Async processing
import asyncio
from concurrent.futures import ThreadPoolExecutor

class AIWorker:
    def __init__(self, db: Database):
        self.db = db
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.site_registry = SiteRegistry(use_gemini=True)
    
    async def process_learning_job_async(self, job_id: str, url: str) -> dict:
        """Process learning job asynchronously"""
        loop = asyncio.get_event_loop()
        
        # Run CPU-intensive tasks in thread pool
        result = await loop.run_in_executor(
            self.executor,
            self.process_learning_job,
            job_id,
            url
        )
        
        return result
```

---

## 🧪 Testing

### **Go Worker Tests**
```go
// internal/worker/handler_test.go
func TestHandleExtractionJob(t *testing.T) {
    // Setup test database
    db := setupTestDB(t)
    defer cleanupTestDB(t, db)
    
    // Create test job
    job := &models.Job{
        ID: uuid.New(),
        URL: "https://example.com/article",
        Domain: "example.com",
        Status: models.StatusQueued,
    }
    
    // Create handler
    handler := NewHandler(jobRepo, configRepo, extractor)
    
    // Test job processing
    task := asynq.NewTask(worker.TypeExtractionJob, job)
    err := handler.HandleExtractionJob(context.Background(), task)
    
    assert.NoError(t, err)
    
    // Verify job was processed
    updatedJob, err := jobRepo.GetByID(context.Background(), job.ID)
    assert.NoError(t, err)
    assert.Equal(t, models.StatusCompleted, updatedJob.Status)
}
```

### **Python Worker Tests**
```python
# tests/test_ai_worker.py
import pytest
from app.ai_worker import AIWorker
from app.database import Database

@pytest.fixture
def ai_worker():
    db = Database("sqlite:///:memory:")
    return AIWorker(db)

def test_process_learning_job(ai_worker):
    """Test learning job processing"""
    job_id = "test-job-123"
    url = "https://example.com/article"
    
    result = ai_worker.process_learning_job(job_id, url)
    
    assert result['success'] == True
    assert 'config' in result
    assert result['config']['domain'] == 'example.com'

def test_extract_with_browser(ai_worker):
    """Test browser extraction"""
    job_id = "test-job-456"
    url = "https://spa-site.com/article"
    
    result = ai_worker.extract_with_browser(job_id, url)
    
    assert result['success'] == True
    assert 'result' in result
```

---

## 🚀 Deployment

### **Docker Configuration**
```dockerfile
# worker-go/Dockerfile
FROM golang:1.21-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN go build -o bin/worker cmd/worker/main.go

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/

COPY --from=builder /app/bin/worker .

CMD ["./worker"]
```

```dockerfile
# worker-python/Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN playwright install chromium

EXPOSE 8081
CMD ["python", "app/main.py"]
```

### **Docker Compose**
```yaml
# docker-compose.yml
services:
  worker-go:
    build: ./worker-go
    environment:
      - REDIS_HOST=redis
      - DATABASE_URL=postgresql://user:password@postgres:5432/article_extraction
      - GEMINI_API_KEY=your-gemini-key
    depends_on:
      - redis
      - postgres

  worker-python:
    build: ./worker-python
    environment:
      - REDIS_HOST=redis
      - DATABASE_URL=postgresql://user:password@postgres:5432/article_extraction
      - GEMINI_API_KEY=your-gemini-key
    depends_on:
      - redis
      - postgres
```

---

## 📚 Next Steps

- **[Go API Documentation](go-api.md)** - API server integration
- **[React Frontend Documentation](react-frontend.md)** - Frontend integration
- **[System Integration](system-integration.md)** - How all parts work together
- **[Deployment Guide](deployment.md)** - Production deployment

---

**The workers provide the core extraction capabilities for the Article Extraction System!**
