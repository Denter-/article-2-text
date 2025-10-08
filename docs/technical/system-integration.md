# System Integration Documentation

**Complete documentation for how all system components work together**

---

## 🎯 System Overview

The Article Extraction System is a distributed architecture that combines Go API services, React frontend, and Python AI workers to provide intelligent article extraction capabilities.

---

## 🏗️ Complete Architecture

### **System Components**
```mermaid
graph TB
    subgraph "Article Extraction System"
        subgraph "Frontend Layer"
            React[React SPA<br/>Port: 3000]
        end
        
        subgraph "API Layer"
            GoAPI[Go API<br/>Port: 8080]
        end
        
        subgraph "Data Layer"
            PostgreSQL[(PostgreSQL<br/>Port: 5432)]
            Redis[(Redis Queue<br/>Port: 6379)]
        end
        
        subgraph "Worker Layer"
            GoWorker[Go Worker<br/>Fast Path]
            PythonWorker[Python AI Worker<br/>Port: 8081]
        end
        
        subgraph "AI Services"
            Gemini[Gemini API]
            Playwright[Playwright]
        end
        
        React <--> GoAPI
        GoAPI <--> PostgreSQL
        GoAPI <--> Redis
        Redis --> GoWorker
        Redis --> PythonWorker
        GoWorker --> PostgreSQL
        PythonWorker --> PostgreSQL
        PythonWorker --> Gemini
        PythonWorker --> Playwright
    end
```

### **Data Flow**
```mermaid
sequenceDiagram
    participant User
    participant React as React Frontend
    participant API as Go API
    participant DB as PostgreSQL
    participant Queue as Redis Queue
    participant GoWorker as Go Worker
    participant PythonWorker as Python AI Worker
    participant AI as AI Services

    User->>React: Extract Article Request
    React->>API: POST /api/v1/extract/single
    API->>DB: Create Job Record
    API->>Queue: Enqueue Job
    API->>React: Job Created (202)
    
    Queue->>GoWorker: Process Job
    GoWorker->>DB: Check Site Config
    
    alt Site Config Exists
        GoWorker->>GoWorker: Extract Content
        GoWorker->>DB: Save Result
    else No Config
        GoWorker->>PythonWorker: Delegate to AI Worker
        PythonWorker->>AI: Learn Site Structure
        PythonWorker->>AI: Generate Descriptions
        PythonWorker->>DB: Save Config & Result
    end
    
    API->>DB: Update Job Status
    API->>React: WebSocket Update
    React->>User: Show Progress
```

---

## 🔄 Complete Job Lifecycle

### **1. Job Creation**
```typescript
// React Frontend
const extractArticle = async (url: string) => {
  const response = await api.extractSingle(url);
  return response.job;
};
```

```go
// Go API Handler
func (h *ExtractHandler) ExtractSingle(c *fiber.Ctx) error {
    // Validate request
    var req models.CreateJobRequest
    if err := c.BodyParser(&req); err != nil {
        return c.Status(400).JSON(fiber.Map{"error": "Invalid request"})
    }
    
    // Create job
    job, err := h.jobSvc.CreateJob(c.Context(), user.ID, &req)
    if err != nil {
        return c.Status(400).JSON(fiber.Map{"error": err.Error()})
    }
    
    // Queue job for processing
    return c.Status(202).JSON(fiber.Map{"job": job})
}
```

### **2. Job Queuing**
```go
// Go API Service
func (s *JobService) CreateJob(ctx context.Context, userID uuid.UUID, req *models.CreateJobRequest) (*models.Job, error) {
    // Create job record
    job := &models.Job{
        UserID:      userID,
        URL:         req.URL,
        Domain:      extractDomain(req.URL),
        Status:      models.StatusQueued,
        CreditsUsed: 1,
    }
    
    // Save to database
    if err := s.jobRepo.Create(ctx, job); err != nil {
        return nil, err
    }
    
    // Queue for processing
    if err := s.queueSvc.EnqueueJob(ctx, job); err != nil {
        return nil, err
    }
    
    return job, nil
}
```

### **3. Worker Processing**
```go
// Go Worker
func (h *Handler) HandleExtractionJob(ctx context.Context, t *asynq.Task) error {
    var job models.Job
    json.Unmarshal(t.Payload(), &job)
    
    // Update status
    h.jobRepo.UpdateStatus(ctx, job.ID, models.StatusProcessing, nil)
    
    // Check site configuration
    config, err := h.configRepo.GetByDomain(ctx, job.Domain)
    if err != nil {
        // No config - delegate to Python worker
        return h.delegateToPythonWorker(ctx, &job)
    }
    
    // Extract using Go worker
    result, err := h.extractor.ExtractArticle(ctx, job.URL, config)
    if err != nil {
        return h.handleExtractionError(ctx, &job, err)
    }
    
    // Complete job
    h.jobRepo.Complete(ctx, &job, result)
    return nil
}
```

### **4. Python AI Worker**
```python
# Python AI Worker
@app.post("/learn")
async def learn_site(request: LearnRequest):
    """Learn extraction rules for a new site using AI"""
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
```

---

## 🔌 API Integration Points

### **Go API ↔ React Frontend**
```typescript
// Frontend API Client
class ApiClient {
  async extractSingle(url: string) {
    return this.request('/api/v1/extract/single', {
      method: 'POST',
      body: JSON.stringify({ url }),
    });
  }
  
  async getJob(jobId: string) {
    return this.request(`/api/v1/jobs/${jobId}`);
  }
  
  async getJobs(limit = 20, offset = 0) {
    return this.request(`/api/v1/jobs?limit=${limit}&offset=${offset}`);
  }
}
```

### **Go API ↔ Go Worker**
```go
// Job Queue Integration
type QueueService struct {
    client *asynq.Client
}

func (s *QueueService) EnqueueJob(ctx context.Context, job *models.Job) error {
    payload, err := json.Marshal(job)
    if err != nil {
        return err
    }
    
    task := asynq.NewTask(TypeExtractionJob, payload)
    _, err = s.client.EnqueueContext(ctx, task)
    return err
}
```

### **Go Worker ↔ Python Worker**
```go
// Go Worker delegates to Python Worker
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
    
    return nil
}
```

---

## 🗄️ Database Integration

### **PostgreSQL Schema**
```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    tier user_tier DEFAULT 'free',
    credits INTEGER DEFAULT 10,
    api_key VARCHAR(64) UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Jobs table
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    url TEXT NOT NULL,
    domain VARCHAR(255) NOT NULL,
    status job_status DEFAULT 'queued',
    worker_type VARCHAR(50),
    progress_percent INTEGER DEFAULT 0,
    progress_message TEXT,
    result_path TEXT,
    markdown_content TEXT,
    title TEXT,
    author TEXT,
    word_count INTEGER,
    image_count INTEGER,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Site configurations table
CREATE TABLE site_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain VARCHAR(255) UNIQUE NOT NULL,
    config_yaml TEXT NOT NULL,
    requires_browser BOOLEAN DEFAULT FALSE,
    learned_by_user_id UUID REFERENCES users(id),
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### **Database Connections**
```go
// Go API Database Connection
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
        return nil, err
    }
    
    poolConfig.MaxConns = int32(cfg.MaxConnections)
    poolConfig.MinConns = int32(cfg.MinConnections)
    
    return pgxpool.NewWithConfig(context.Background(), poolConfig)
}
```

```python
# Python Worker Database Connection
class Database:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.connection = None
    
    def connect(self):
        """Connect to PostgreSQL database"""
        self.connection = psycopg2.connect(self.database_url)
    
    def get_job(self, job_id: str) -> dict:
        """Get job by ID"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
        result = cursor.fetchone()
        cursor.close()
        return result
    
    def update_job_status(self, job_id: str, status: str, message: str = None):
        """Update job status"""
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE jobs SET status = %s, progress_message = %s WHERE id = %s",
            (status, message, job_id)
        )
        self.connection.commit()
        cursor.close()
```

---

## 🔄 Real-time Updates

### **WebSocket Integration**
```go
// Go API WebSocket Hub
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

```typescript
// React Frontend WebSocket
export function useWebSocket() {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const { user } = useAuth();

  useEffect(() => {
    if (!user) return;

    const ws = new WebSocket(`ws://localhost:8080/api/v1/ws`);
    
    ws.onopen = () => {
      ws.send(JSON.stringify({
        type: 'auth',
        token: localStorage.getItem('token'),
      }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleWebSocketMessage(data);
    };

    setSocket(ws);
    return () => ws.close();
  }, [user]);

  const handleWebSocketMessage = (data: any) => {
    switch (data.type) {
      case 'job_update':
        queryClient.setQueryData(['jobs', data.jobId], (old: any) => ({
          ...old,
          progress_percent: data.progress,
          progress_message: data.message,
        }));
        break;
      case 'job_completed':
        queryClient.invalidateQueries(['jobs']);
        break;
    }
  };

  return socket;
}
```

---

## 🧠 AI Integration Flow

### **Site Learning Process**
```python
# Python AI Worker - Site Learning
def learn_site(self, url: str, max_iterations: int = 3) -> tuple[bool, dict, str]:
    """Learn extraction rules for a new site using AI"""
    
    # Download page content
    html_content = self.fetch_page_content(url)
    
    # Check if browser is required
    requires_browser = self.detect_javascript_requirements(html_content)
    
    # Learn extraction rules using AI
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
# Python AI Worker - Image Processing
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

## 🔧 Configuration Management

### **Environment Variables**
```env
# Go API
API_PORT=8080
API_HOST=0.0.0.0
DATABASE_URL=postgresql://user:password@localhost:5432/article_extraction
REDIS_HOST=localhost
REDIS_PORT=6379
JWT_SECRET=your-super-secret-jwt-key
GEMINI_API_KEY=your_gemini_api_key

# React Frontend
VITE_API_URL=http://localhost:8080
VITE_WS_URL=ws://localhost:8080

# Python Worker
DATABASE_URL=postgresql://user:password@localhost:5432/article_extraction
GEMINI_API_KEY=your_gemini_api_key
LOG_LEVEL=info
```

### **Site Configuration Files**
```yaml
# config/sites/example.com.yaml
domain: example.com
requires_browser: false
selectors:
  title: h1
  content: .article-content
  author: .author-name
  date: .publish-date
exclude_selectors:
  - .navigation
  - .sidebar
  - .comments
  - .ads
filters:
  min_length: 100
  max_length: 50000
  remove_scripts: true
  remove_styles: true
```

---

## 🚀 Deployment Architecture

### **Docker Compose Setup**
```yaml
# docker-compose.yml
version: '3.8'

services:
  # Database
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: article_extraction
      POSTGRES_USER: article_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  # Redis
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # Go API
  api:
    build: ./api
    environment:
      - DATABASE_URL=postgresql://article_user:secure_password@postgres:5432/article_extraction
      - REDIS_HOST=redis
      - JWT_SECRET=your-super-secret-jwt-key
      - GEMINI_API_KEY=your_gemini_api_key
    ports:
      - "8080:8080"
    depends_on:
      - postgres
      - redis

  # React Frontend
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - api

  # Go Worker
  worker-go:
    build: ./worker-go
    environment:
      - DATABASE_URL=postgresql://article_user:secure_password@postgres:5432/article_extraction
      - REDIS_HOST=redis
      - GEMINI_API_KEY=your_gemini_api_key
    depends_on:
      - postgres
      - redis

  # Python Worker
  worker-python:
    build: ./worker-python
    environment:
      - DATABASE_URL=postgresql://article_user:secure_password@postgres:5432/article_extraction
      - REDIS_HOST=redis
      - GEMINI_API_KEY=your_gemini_api_key
    depends_on:
      - postgres
      - redis

volumes:
  postgres_data:
```

### **Production Deployment**
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  # Load Balancer
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api
      - frontend

  # Go API (Multiple instances)
  api:
    build: ./api
    environment:
      - DATABASE_URL=postgresql://article_user:secure_password@postgres:5432/article_extraction
      - REDIS_HOST=redis
      - JWT_SECRET=your-super-secret-jwt-key
      - GEMINI_API_KEY=your_gemini_api_key
    deploy:
      replicas: 3
    depends_on:
      - postgres
      - redis

  # Workers (Multiple instances)
  worker-go:
    build: ./worker-go
    environment:
      - DATABASE_URL=postgresql://article_user:secure_password@postgres:5432/article_extraction
      - REDIS_HOST=redis
      - GEMINI_API_KEY=your_gemini_api_key
    deploy:
      replicas: 5
    depends_on:
      - postgres
      - redis

  worker-python:
    build: ./worker-python
    environment:
      - DATABASE_URL=postgresql://article_user:secure_password@postgres:5432/article_extraction
      - REDIS_HOST=redis
      - GEMINI_API_KEY=your_gemini_api_key
    deploy:
      replicas: 2
    depends_on:
      - postgres
      - redis
```

---

## 📊 Monitoring and Observability

### **Health Checks**
```go
// Go API Health Check
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

```python
# Python Worker Health Check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ai-worker",
        "gemini_enabled": ai_worker.site_registry.use_gemini if ai_worker else False
    }
```

### **Metrics Collection**
```go
// Go API Metrics
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

## 🧪 Testing Integration

### **End-to-End Testing**
```typescript
// Frontend E2E Tests
describe('Article Extraction Flow', () => {
  it('should extract article successfully', async () => {
    // Login
    await page.goto('http://localhost:3000/login');
    await page.fill('[data-testid="email"]', 'test@example.com');
    await page.fill('[data-testid="password"]', 'password123');
    await page.click('[data-testid="login-button"]');
    
    // Extract article
    await page.goto('http://localhost:3000/');
    await page.fill('[data-testid="url-input"]', 'https://example.com/article');
    await page.click('[data-testid="extract-button"]');
    
    // Wait for completion
    await page.waitForSelector('[data-testid="job-completed"]', { timeout: 30000 });
    
    // Verify result
    const result = await page.textContent('[data-testid="job-result"]');
    expect(result).toContain('Article extracted successfully');
  });
});
```

### **Integration Testing**
```go
// Go API Integration Tests
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

## 📚 Next Steps

- **[Go API Documentation](go-api.md)** - Detailed API documentation
- **[React Frontend Documentation](react-frontend.md)** - Frontend implementation
- **[Workers Documentation](workers.md)** - Worker implementation
- **[Deployment Guide](deployment.md)** - Production deployment

---

**The system integration provides a complete, scalable solution for intelligent article extraction!**
