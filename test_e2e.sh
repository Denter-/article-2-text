#!/bin/bash
echo "🧪 End-to-End Test: API → Queue → Worker → Result"
echo "=================================================="
echo ""

# Login
LOGIN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}')
TOKEN=$(echo $LOGIN | grep -o '"token":"[^"]*' | cut -d'"' -f4)

echo "1️⃣ Creating extraction job..."
JOB=$(curl -s -X POST http://localhost:8080/api/v1/extract/single \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.forentrepreneurs.com/startup-metrics/"}')
JOB_ID=$(echo $JOB | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)
echo "Job created: $JOB_ID"
echo ""

echo "2️⃣ Waiting for worker to process (15 seconds)..."
for i in {1..15}; do
  echo -n "."
  sleep 1
done
echo ""
echo ""

echo "3️⃣ Checking job status..."
STATUS=$(curl -s http://localhost:8080/api/v1/jobs/$JOB_ID -H "Authorization: Bearer $TOKEN")
echo "$STATUS" | head -20
echo ""

echo "4️⃣ Checking if file was created..."
RESULT_PATH=$(echo $STATUS | grep -o '"result_path":"[^"]*' | cut -d'"' -f4)
if [ -n "$RESULT_PATH" ] && [ -f "$RESULT_PATH" ]; then
  echo "✅ File created: $RESULT_PATH"
  echo "File size: $(du -h $RESULT_PATH | cut -f1)"
  echo ""
  echo "First 30 lines:"
  head -30 "$RESULT_PATH"
else
  echo "⚠️ File not found or still processing"
fi

echo ""
echo "=================================================="
echo "End-to-end test complete!"
