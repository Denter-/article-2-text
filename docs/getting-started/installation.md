# Installation Guide

**Set up the Article Extraction System on your machine**

---

## 🎯 Choose Your Installation Type

### **Option 1: Python CLI Only (Simplest)**
For personal use, research, or simple extraction tasks.

### **Option 2: Full Service (Complete)**
For API access, web interface, and production deployment.

---

## 🐍 Python CLI Installation

### **System Requirements**
- Python 3.8 or higher
- 4GB RAM minimum
- 2GB free disk space

### **Step 1: Clone the Repository**
```bash
git clone <repository-url>
cd article-2-text
```

### **Step 2: Create Virtual Environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### **Step 3: Install Dependencies**
```bash
pip install -r requirements.txt
```

### **Step 4: Install Playwright (Optional)**
For JavaScript-heavy sites:
```bash
playwright install chromium
```

### **Step 5: Set Up API Key (Required for AI Learning)**
Create `.env` file:
```bash
# Create .env file in project root
echo "GEMINI_API_KEY=your-api-key-here" > .env
```

Edit `.env` and add your Gemini API key:
```env
GEMINI_API_KEY=your_actual_key_here
```

Get your key from: https://makersuite.google.com/app/apikey

### **Step 6: Test Installation**
```bash
# Test with a real article (this will use AI learning)
python src/article_extractor.py --gemini https://www.forentrepreneurs.com/top-two-reasons-for-churn/

# Check results
ls results/
```

---

## 🚀 Full Service Installation

### **System Requirements**
- Python 3.8+ and Go 1.21+
- PostgreSQL 15+
- Redis 7+
- Node.js 18+
- 8GB RAM minimum
- 10GB free disk space

### **Step 1: Install System Dependencies**

#### **Ubuntu/Debian:**
```bash
# Install system packages
sudo apt update
sudo apt install postgresql postgresql-contrib redis-server nodejs npm

# Install Go
wget https://go.dev/dl/go1.21.0.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.21.0.linux-amd64.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
source ~/.bashrc
```

#### **macOS:**
```bash
# Install with Homebrew
brew install postgresql redis go node
```

#### **Windows:**
- Download and install PostgreSQL, Redis, Go, and Node.js from their official websites

### **Step 2: Set Up Database**
```bash
# Start PostgreSQL
sudo systemctl start postgresql  # Linux
brew services start postgresql    # macOS

# Create database
sudo -u postgres createdb article_extraction

# Set up database schema (run migrations)
cd api && go run cmd/migrate/main.go
```

### **Step 3: Set Up Redis**
```bash
# Start Redis
sudo systemctl start redis-server  # Linux
brew services start redis          # macOS

# Test Redis connection
redis-cli ping  # Should return PONG
```

### **Step 4: Install Application Dependencies**
```bash
# Python dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Go dependencies
cd api && go mod download
cd ../worker-go && go mod download

# Frontend dependencies
cd ../frontend && npm install
```

### **Step 5: Run Database Migrations**
```bash
# Set up database schema
psql -U postgres -d article_extraction -f shared/db/migrations/001_init.sql
psql -U postgres -d article_extraction -f shared/db/migrations/002_users.sql
psql -U postgres -d article_extraction -f shared/db/migrations/003_jobs.sql
psql -U postgres -d article_extraction -f shared/db/migrations/004_site_configs.sql
psql -U postgres -d article_extraction -f shared/db/migrations/005_usage_logs.sql
```

### **Step 6: Configure Environment**
```bash
# Create .env file in project root
cat > .env << EOF
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/article_extraction

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# API
JWT_SECRET=dev-secret-change-in-production-min-32-chars
GEMINI_API_KEY=your_gemini_api_key

# Server
API_PORT=8080
EOF
```

### **Step 7: Start All Services**
```bash
# Terminal 1: Start Go API
cd api && go run cmd/api/main.go

# Terminal 2: Start Go Worker
cd worker-go && go run cmd/worker/main.go

# Terminal 3: Start Python AI Worker
cd worker-python && source venv/bin/activate && python app/main.py

# Terminal 4: Start React Frontend
cd frontend && npm run dev
```

### **Step 8: Test Full Installation**
```bash
# Test API health
curl http://localhost:8080/health

# Test frontend (runs on port 5173)
open http://localhost:5173

# Test article extraction via web interface
# 1. Go to http://localhost:5173
# 2. Login with test@example.com / password
# 3. Submit a test URL
# 4. Watch the job process in real-time
```

---

## 🔧 Troubleshooting

### **Common Issues**

#### **Python Import Errors**
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

#### **Database Connection Issues**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check if database exists
psql -U postgres -l | grep article_extraction
```

#### **Redis Connection Issues**
```bash
# Check Redis status
sudo systemctl status redis-server

# Test Redis connection
redis-cli ping
```

#### **Go Build Errors**
```bash
# Check Go installation
go version

# Clean and rebuild
cd api && go clean && go build
```

#### **Frontend Build Errors**
```bash
# Clear node modules and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
```

#### **Python AI Worker Issues**
```bash
# Check if Gemini API key is set
echo $GEMINI_API_KEY

# Test Gemini API connection
cd worker-python && source venv/bin/activate && python -c "from google import genai; print('Gemini API working')"

# Install missing dependencies
cd worker-python && source venv/bin/activate && pip install google-genai

# Check worker logs
cd worker-python && source venv/bin/activate && python app/main.py
```

#### **Job Processing Issues**
```bash
# Check if all workers are running
ps aux | grep -E "(go run|python app/main.py)"

# Check Redis queue
redis-cli llen asynq:queues:learning

# Check database for job status
psql -U postgres -d article_extraction -c "SELECT status, COUNT(*) FROM jobs GROUP BY status;"
```

#### **Database Schema Issues**
```bash
# Add missing columns if needed
psql -U postgres -d article_extraction -c "ALTER TABLE site_configs ADD COLUMN IF NOT EXISTS last_checked_at TIMESTAMP WITH TIME ZONE;"
psql -U postgres -d article_extraction -c "ALTER TABLE site_configs ADD COLUMN IF NOT EXISTS next_check_at TIMESTAMP WITH TIME ZONE;"
```

### **Performance Issues**

#### **Slow Extraction**
- Ensure you have enough RAM (8GB+ recommended)
- Check if Playwright is installed for JavaScript sites
- Consider using the Go worker for simple sites

#### **Memory Issues**
- Increase system memory
- Use the Python CLI for single extractions
- Consider running workers separately

---

## ✅ Verification

### **Python CLI Test**
```bash
python src/article_extractor.py https://example.com/article
```

### **API Test**
```bash
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

### **Frontend Test**
Open http://localhost:3000 and try extracting an article.

---

## 🎯 Next Steps

- **[Python CLI Quick Start](quickstart.md)** - Extract your first article
- **[API Setup](api-setup.md)** - Configure the full service
- **[System Overview](../README.md)** - Understand how it works

---

**Need help?** Check the [troubleshooting section](#troubleshooting) or see [System Overview](../README.md) for more details.