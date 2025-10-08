# Deployment Guide

**Deploy the Article Extraction Service to production**

---

## 🎯 Deployment Options

### **Option 1: Docker Compose (Recommended)**
Easy deployment with all services in containers.

### **Option 2: Manual Deployment**
Deploy services individually on servers.

### **Option 3: Cloud Deployment**
Deploy to cloud platforms (AWS, GCP, Azure).

---

## 🐳 Docker Compose Deployment

### **Prerequisites**
- Docker 20.10+
- Docker Compose 2.0+
- 8GB RAM minimum
- 20GB disk space

### **Step 1: Prepare Environment**
```bash
# Clone repository
git clone <repository-url>
cd article-2-text

# Create production environment file
cp config/.env.example config/.env.production
```

### **Step 2: Configure Production Settings**
```env
# config/.env.production
# Database
DATABASE_URL=postgresql://user:password@postgres:5432/article_extraction
DB_HOST=postgres
DB_PORT=5432
DB_USER=article_user
DB_PASSWORD=secure_password
DB_NAME=article_extraction

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=secure_redis_password

# API Server
API_PORT=8080
API_HOST=0.0.0.0
JWT_SECRET=your-super-secret-jwt-key-for-production
JWT_EXPIRY_HOURS=24

# AI Services
GEMINI_API_KEY=your_production_gemini_key

# Storage
STORAGE_TYPE=local
STORAGE_PATH=/app/storage

# Production settings
ENVIRONMENT=production
LOG_LEVEL=info
```

### **Step 3: Create Docker Compose File**
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
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

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass secure_redis_password
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  api:
    build:
      context: ./api
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://article_user:secure_password@postgres:5432/article_extraction
      - REDIS_HOST=redis
      - REDIS_PASSWORD=secure_redis_password
      - JWT_SECRET=your-super-secret-jwt-key-for-production
      - GEMINI_API_KEY=your_production_gemini_key
    ports:
      - "8080:8080"
    depends_on:
      - postgres
      - redis

  worker-go:
    build:
      context: ./worker-go
      dockerfile: Dockerfile
    environment:
      - REDIS_HOST=redis
      - REDIS_PASSWORD=secure_redis_password
    depends_on:
      - redis

  worker-python:
    build:
      context: ./worker-python
      dockerfile: Dockerfile
    environment:
      - REDIS_HOST=redis
      - REDIS_PASSWORD=secure_redis_password
      - GEMINI_API_KEY=your_production_gemini_key
    depends_on:
      - redis

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    depends_on:
      - api

volumes:
  postgres_data:
  redis_data:
```

### **Step 4: Deploy Services**
```bash
# Build and start all services
docker-compose -f docker-compose.prod.yml up -d

# Check service status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### **Step 5: Run Database Migrations**
```bash
# Run migrations
docker-compose -f docker-compose.prod.yml exec api ./migrate.sh

# Verify database
docker-compose -f docker-compose.prod.yml exec postgres psql -U article_user -d article_extraction -c "\dt"
```

---

## 🖥️ Manual Deployment

### **Server Requirements**
- Ubuntu 20.04+ or CentOS 8+
- 8GB RAM minimum
- 20GB disk space
- Root or sudo access

### **Step 1: Install Dependencies**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y postgresql postgresql-contrib redis-server nginx

# Install Go
wget https://go.dev/dl/go1.21.0.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.21.0.linux-amd64.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
source ~/.bashrc

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

### **Step 2: Set Up Database**
```bash
# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql -c "CREATE DATABASE article_extraction;"
sudo -u postgres psql -c "CREATE USER article_user WITH PASSWORD 'secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE article_extraction TO article_user;"
```

### **Step 3: Set Up Redis**
```bash
# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Configure Redis password
sudo nano /etc/redis/redis.conf
# Add: requirepass secure_redis_password
sudo systemctl restart redis-server
```

### **Step 4: Deploy Application**
```bash
# Create application directory
sudo mkdir -p /opt/article-extraction
sudo chown $USER:$USER /opt/article-extraction
cd /opt/article-extraction

# Clone repository
git clone <repository-url> .

# Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Build Go services
cd api && go build -o bin/api cmd/api/main.go
cd ../worker-go && go build -o bin/worker cmd/worker/main.go

# Build frontend
cd ../frontend
npm install
npm run build
```

### **Step 5: Configure Services**
```bash
# Create systemd service files
sudo nano /etc/systemd/system/article-api.service
```

```ini
[Unit]
Description=Article Extraction API
After=postgresql.service redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/article-extraction
ExecStart=/opt/article-extraction/api/bin/api
Environment=DATABASE_URL=postgresql://article_user:secure_password@localhost:5432/article_extraction
Environment=REDIS_HOST=localhost
Environment=REDIS_PASSWORD=secure_redis_password
Environment=JWT_SECRET=your-super-secret-jwt-key-for-production
Environment=GEMINI_API_KEY=your_production_gemini_key
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Create worker service
sudo nano /etc/systemd/system/article-worker.service
```

```ini
[Unit]
Description=Article Extraction Worker
After=redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/article-extraction
ExecStart=/opt/article-extraction/worker-go/bin/worker
Environment=REDIS_HOST=localhost
Environment=REDIS_PASSWORD=secure_redis_password
Restart=always

[Install]
WantedBy=multi-user.target
```

### **Step 6: Start Services**
```bash
# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable article-api
sudo systemctl enable article-worker
sudo systemctl start article-api
sudo systemctl start article-worker

# Check status
sudo systemctl status article-api
sudo systemctl status article-worker
```

---

## ☁️ Cloud Deployment

### **AWS Deployment**

#### **Using AWS ECS**
```yaml
# task-definition.json
{
  "family": "article-extraction",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "your-registry/article-api:latest",
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql://user:password@rds-endpoint:5432/article_extraction"
        }
      ]
    }
  ]
}
```

#### **Using AWS EKS**
```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: article-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: article-api
  template:
    metadata:
      labels:
        app: article-api
    spec:
      containers:
      - name: api
        image: your-registry/article-api:latest
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: article-secrets
              key: database-url
```

### **Google Cloud Deployment**

#### **Using Cloud Run**
```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/article-api', './api']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/article-api']
  - name: 'gcr.io/cloud-builders/gcloud'
    args: ['run', 'deploy', 'article-api', '--image', 'gcr.io/$PROJECT_ID/article-api', '--platform', 'managed', '--region', 'us-central1']
```

---

## 🔧 Production Configuration

### **Environment Variables**
```env
# Production settings
ENVIRONMENT=production
LOG_LEVEL=info
LOG_FORMAT=json

# Security
JWT_SECRET=your-super-secret-jwt-key-for-production
BCRYPT_COST=12

# Database
DB_MAX_CONNECTIONS=50
DB_MIN_CONNECTIONS=10

# Redis
REDIS_POOL_SIZE=20

# Rate limiting
RATE_LIMIT_FREE=10
RATE_LIMIT_PRO=100
RATE_LIMIT_WINDOW=3600

# Storage
STORAGE_TYPE=s3
STORAGE_BUCKET=article-extraction-results
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
```

### **Nginx Configuration**
```nginx
# /etc/nginx/sites-available/article-extraction
server {
    listen 80;
    server_name your-domain.com;

    # API
    location /api/ {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Frontend
    location / {
        root /opt/article-extraction/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Storage
    location /storage/ {
        alias /opt/article-extraction/storage/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## 📊 Monitoring and Logging

### **Application Logs**
```bash
# View API logs
sudo journalctl -u article-api -f

# View worker logs
sudo journalctl -u article-worker -f

# View database logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

### **Health Checks**
```bash
# API health
curl http://localhost:8080/health

# Database health
psql -U article_user -d article_extraction -c "SELECT 1;"

# Redis health
redis-cli ping
```

### **Performance Monitoring**
```bash
# Check service status
sudo systemctl status article-api article-worker

# Check resource usage
htop
df -h
free -h
```

---

## 🔒 Security Considerations

### **Database Security**
```sql
-- Create read-only user for monitoring
CREATE USER monitor_user WITH PASSWORD 'monitor_password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO monitor_user;
```

### **API Security**
```bash
# Set up SSL certificates
sudo certbot --nginx -d your-domain.com

# Configure firewall
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### **Environment Security**
```bash
# Secure environment files
chmod 600 config/.env.production
chown root:root config/.env.production
```

---

## 📈 Scaling

### **Horizontal Scaling**
```yaml
# docker-compose.scale.yml
version: '3.8'
services:
  api:
    deploy:
      replicas: 3
  worker-go:
    deploy:
      replicas: 5
  worker-python:
    deploy:
      replicas: 2
```

### **Load Balancing**
```nginx
# nginx.conf
upstream api_backend {
    server localhost:8080;
    server localhost:8081;
    server localhost:8082;
}

server {
    location /api/ {
        proxy_pass http://api_backend;
    }
}
```

---

## 🎯 Next Steps

- **[System Architecture](architecture.md)** - Understand the system
- **[API Reference](../usage/api-reference.md)** - Use the deployed API
- **[Monitoring Guide](../development/monitoring.md)** - Monitor your deployment

---

**Your Article Extraction Service is now deployed and ready for production use!**



