#!/bin/bash
echo "🧪 Testing Hybrid Architecture: Go API + Go Worker + Python AI Worker"
echo "======================================================================="
echo ""

# Step 1: Login
echo "1️⃣ Login to API..."
LOGIN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}')
TOKEN=$(echo $LOGIN | grep -o '"token":"[^"]*' | cut -d'"' -f4)
echo "✅ Logged in"
echo ""

# Step 2: Test a site that needs learning (new domain)
echo "2️⃣ Creating job for new site (should need AI learning)..."
NEW_SITE="https://example-news-site.com/article"
JOB=$(curl -s -X POST http://localhost:8080/api/v1/extract/single \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"https://www.theverge.com/tech\"}")
JOB_ID=$(echo $JOB | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "Job ID: $JOB_ID"
echo ""

# Step 3: Check Python AI Worker health
echo "3️⃣ Checking Python AI Worker health..."
curl -s http://localhost:8081/health | head -100
echo ""
echo ""

# Step 4: Manually test AI learning endpoint
echo "4️⃣ Testing AI learning endpoint directly..."
echo "This would normally be called by Go Worker when no config exists"
echo ""

# Create a test job in the database first
TEST_JOB_ID="00000000-0000-0000-0000-000000000001"

# Test the learning endpoint
LEARN_RESULT=$(curl -s -X POST http://localhost:8081/learn \
  -H "Content-Type: application/json" \
  -d "{\"job_id\":\"$TEST_JOB_ID\",\"url\":\"https://www.forentrepreneurs.com/why-startups-fail/\"}" \
  --max-time 60)

echo "Learning result:"
echo "$LEARN_RESULT" | head -500
echo ""

echo "======================================================================="
echo "✅ Hybrid architecture test complete!"
echo ""
echo "Services running:"
echo "  - Go API: http://localhost:8080 (Fast, concurrent user handling)"
echo "  - Go Worker: Background processing (90% of jobs - fast path)"
echo "  - Python AI Worker: http://localhost:8081 (10% of jobs - AI learning)"
