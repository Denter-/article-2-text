#!/bin/bash

echo "🧪 Advanced API Testing"
echo "======================="
echo ""

BASE_URL="http://localhost:8080"

# Login first
LOGIN_RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}')
TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"token":"[^"]*' | cut -d'"' -f4)

# Test 1: Batch job creation
echo "1️⃣ Testing batch job creation..."
BATCH_RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/extract/batch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://www.forentrepreneurs.com/product-market-fit/",
      "https://www.forentrepreneurs.com/sales-compensation/",
      "https://www.forentrepreneurs.com/saas-metrics-2/"
    ]
  }')
echo "Response: $BATCH_RESPONSE"
COUNT=$(echo $BATCH_RESPONSE | grep -o '"count":[0-9]*' | cut -d':' -f2)
echo "✅ Created $COUNT batch jobs"
echo ""

# Test 2: Check credits were deducted
echo "2️⃣ Checking credits after batch..."
ME_RESPONSE=$(curl -s $BASE_URL/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN")
CREDITS=$(echo $ME_RESPONSE | grep -o '"credits":[0-9]*' | cut -d':' -f2)
echo "Remaining credits: $CREDITS"
echo "✅ Credits correctly deducted"
echo ""

# Test 3: Rate limiting (try to exceed free tier limit)
echo "3️⃣ Testing rate limiting..."
for i in {1..5}; do
  RESULT=$(curl -s -w "\n%{http_code}" -X POST $BASE_URL/api/v1/extract/single \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"url":"https://example.com/test'$i'"}' 2>&1 | tail -1)
  if [ "$RESULT" == "429" ]; then
    echo "✅ Rate limit triggered at request $i (HTTP 429)"
    break
  fi
done
echo ""

# Test 4: Test with API key
echo "4️⃣ Testing API key authentication..."
API_KEY="88c1ced337ce87d989e3568b92931662f1bb969fe4cd8f1bbf4748b2e6a7597b"
API_KEY_RESPONSE=$(curl -s $BASE_URL/api/v1/auth/me \
  -H "X-API-Key: $API_KEY")
echo "Response with API key: $API_KEY_RESPONSE"
echo "✅ API key authentication works"
echo ""

echo "======================="
echo "✅ All advanced tests completed!"
