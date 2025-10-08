# API Setup Guide

**Set up the full Article Extraction Service with API, database, and web interface**

---

## 🎯 What You'll Get

After completing this setup, you'll have:
- ✅ **REST API** - Programmatic access to extraction services
- ✅ **Web Interface** - React frontend for testing and management
- ✅ **Database** - PostgreSQL with user management and job tracking
- ✅ **Workers** - Both Go (fast) and Python (AI-powered) extraction workers
- ✅ **Authentication** - JWT-based user authentication
- ✅ **Job Queue** - Redis-based job processing

---

## 📋 Prerequisites

Make sure you've completed the [Installation Guide](installation.md) first.

**Required Services:**
- PostgreSQL 15+ running
- Redis 7+ running
- Go 1.21+ installed
- Node.js 18+ installed

---

## 🗄️ Database Setup

### **Step 1: Create Database**
```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE article_extraction;
CREATE USER article_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE article_extraction TO article_user;
\q
```

### **Step 2: Run Migrations**
```bash
# Run all database migrations
for migration in shared/db/migrations/*.sql; do
    echo "Running $(basename $migration)..."
    psql -U article_user -d article_extraction -f "$migration"
done
```

### **Step 3: Verify Database**
```bash
# Check tables were created
psql -U article_user -d article_extraction -c "\dt"
```

You should see:
- `users` - User accounts and authentication
- `jobs` - Extraction jobs and status
- `site_configs` - Learned site configurations
- `usage_logs` - Usage tracking and analytics

---

## ⚙️ Configuration

### **Step 1: Environment Variables**
```bash
# Copy configuration template
cp config/.env.example config/.env

# Edit configuration
nano config/.env
```

### **Step 2: Required Settings**
```env
# Database
DATABASE_URL=postgresql://article_user:your_password@localhost:5432/article_extraction
DB_HOST=localhost
DB_PORT=5432
DB_USER=article_user
DB_PASSWORD=your_password
DB_NAME=article_extraction

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# API Server
API_PORT=8080
API_HOST=0.0.0.0
JWT_SECRET=your-super-secret-jwt-key-change-in-production
JWT_EXPIRY_HOURS=24

# AI Services
GEMINI_API_KEY=your_gemini_api_key_here

# Workers
QUEUE_CONCURRENCY=10
QUEUE_GO_WORKER_COUNT=5
QUEUE_PYTHON_WORKER_COUNT=2

# Storage
STORAGE_TYPE=local
STORAGE_PATH=./storage
```

### **Step 3: Create Storage Directory**
```bash
mkdir -p storage
chmod 755 storage
```

---

## 🚀 Start Services

### **Option 1: Development Mode (All in One)**
```bash
# Start all services with one command
./scripts/dev-start.sh
```

This will start:
- Go API server (port 8080)
- Go worker
- Python AI worker
- React frontend (port 3000)

### **Option 2: Manual Start (Recommended for Production)**

#### **Start API Server**
```bash
cd api
go run cmd/api/main.go
```

#### **Start Go Worker**
```bash
cd worker-go
go run cmd/worker/main.go
```

#### **Start Python AI Worker**
```bash
cd worker-python
source ../venv/bin/activate
python app/main.py
```

#### **Start Frontend**
```bash
cd frontend
npm run dev
```

---

## 🧪 Test the Setup

### **Step 1: Test API Health**
```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "article-extraction-api"
}
```

### **Step 2: Test User Registration**
```bash
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'
```

### **Step 3: Test Login**
```bash
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'
```

Save the token from the response for API calls.

### **Step 4: Test Article Extraction**
```bash
# Use the token from login
curl -X POST http://localhost:8080/api/v1/extract/single \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/article"
  }'
```

### **Step 5: Test Web Interface**
Open http://localhost:3000 in your browser and:
1. Register a new account
2. Extract an article
3. View the results

---

## 🔧 Service Management

### **Check Service Status**
```bash
# Check if services are running
ps aux | grep -E "(api|worker|frontend)"

# Check database connections
psql -U article_user -d article_extraction -c "SELECT COUNT(*) FROM users;"

# Check Redis
redis-cli ping
```

### **View Logs**
```bash
# API logs
tail -f logs/api.log

# Worker logs
tail -f logs/worker.log

# Database logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

### **Restart Services**
```bash
# Stop all services
pkill -f "api|worker|frontend"

# Start again
./scripts/dev-start.sh
```

---

## 🎯 Next Steps

### **For API Users**
- **[REST API Reference](../usage/api-reference.md)** - Complete API documentation
- **[Authentication Guide](../usage/api-reference.md#authentication)** - How to authenticate
- **[Job Management](../usage/api-reference.md#jobs)** - How to track extraction jobs

### **For Web Users**
- **[Web Interface Guide](../usage/frontend-interface.md)** - Using the React frontend
- **[Quality Testing](../usage/frontend-interface.md#quality-testing)** - Testing extraction quality

### **For Developers**
- **[System Architecture](../technical/architecture.md)** - How everything works
- **[Contributing Guide](../development/contributing.md)** - How to contribute

---

## 🆘 Troubleshooting

### **Common Issues**

#### **Database Connection Failed**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check database exists
psql -U article_user -d article_extraction -c "SELECT 1;"
```

#### **Redis Connection Failed**
```bash
# Check Redis is running
sudo systemctl status redis-server

# Test connection
redis-cli ping
```

#### **API Server Won't Start**
```bash
# Check port is available
netstat -tlnp | grep 8080

# Check Go installation
go version

# Rebuild API
cd api && go clean && go build
```

#### **Workers Not Processing Jobs**
```bash
# Check Redis queue
redis-cli llen asynq:extraction:job

# Check worker logs
tail -f logs/worker.log
```

#### **Frontend Build Errors**
```bash
# Clear and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

---

## ✅ Verification Checklist

- [ ] PostgreSQL database created and migrations run
- [ ] Redis server running and accessible
- [ ] API server starts without errors
- [ ] Health endpoint returns 200
- [ ] User registration works
- [ ] User login returns JWT token
- [ ] Article extraction creates job
- [ ] Workers process jobs
- [ ] Frontend loads and connects to API
- [ ] All services can communicate

---

**Setup complete!** You now have a full Article Extraction Service running. See the [Usage Guides](../usage/) to learn how to use it.



