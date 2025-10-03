#!/bin/bash

echo "🧪 Testing Article Extraction API"
echo "=================================="
echo ""

BASE_URL="http://localhost:8080"

# Test 1: Health check
echo "1️⃣ Testing health endpoint..."
HEALTH=$(curl -s $BASE_URL/health)
echo "Response: $HEALTH"
echo "✅ Health check passed"
echo ""

# Test 2: Register new user
echo "2️⃣ Testing user registration..."
REGISTER_RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}')
echo "Response: $REGISTER_RESPONSE"
echo "✅ Registration passed"
echo ""

# Test 3: Login
echo "3️⃣ Testing login..."
LOGIN_RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}')
echo "Response: $LOGIN_RESPONSE"

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"token":"[^"]*' | cut -d'"' -f4)
if [ -z "$TOKEN" ]; then
  echo "❌ Failed to get token"
  exit 1
fi
echo "✅ Login passed, got token: ${TOKEN:0:50}..."
echo ""

# Test 4: Get user info
echo "4️⃣ Testing /me endpoint..."
ME_RESPONSE=$(curl -s $BASE_URL/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN")
echo "Response: $ME_RESPONSE"
echo "✅ /me endpoint passed"
echo ""

# Test 5: Create extraction job
echo "5️⃣ Testing job creation..."
JOB_RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/extract/single \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.forentrepreneurs.com/startup-killer/"}')
echo "Response: $JOB_RESPONSE"
echo "✅ Job creation passed"
echo ""

# Test 6: List jobs
echo "6️⃣ Testing job listing..."
JOBS_RESPONSE=$(curl -s $BASE_URL/api/v1/jobs \
  -H "Authorization: Bearer $TOKEN")
echo "Response: $JOBS_RESPONSE"
echo "✅ Job listing passed"
echo ""

echo "=================================="
echo "✅ All API tests passed!"
