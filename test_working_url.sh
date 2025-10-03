#!/bin/bash
echo "🧪 Testing with existing URL"
echo "=============================="

LOGIN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}')
TOKEN=$(echo $LOGIN | grep -o '"token":"[^"]*' | cut -d'"' -f4)

echo "Creating job for working URL..."
JOB=$(curl -s -X POST http://localhost:8080/api/v1/extract/single \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.forentrepreneurs.com/product-market-fit/"}')
JOB_ID=$(echo $JOB | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)
echo "Job ID: $JOB_ID"

echo ""
echo "Waiting 15 seconds for processing..."
for i in {1..15}; do echo -n "."; sleep 1; done
echo ""

echo "Checking status..."
curl -s http://localhost:8080/api/v1/jobs/$JOB_ID -H "Authorization: Bearer $TOKEN" | head -c 500
echo ""
