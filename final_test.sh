#!/bin/bash
LOGIN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login -H "Content-Type: application/json" -d '{"email":"test@example.com","password":"password123"}')
TOKEN=$(echo $LOGIN | grep -o '"token":"[^"]*' | cut -d'"' -f4)

echo "Creating extraction job..."
JOB_RESP=$(curl -s -X POST http://localhost:8080/api/v1/extract/single -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"url":"https://www.forentrepreneurs.com/saas-metrics-2/"}')
echo "$JOB_RESP"

JOB_ID=$(echo $JOB_RESP | grep -o '"job_id":"[^"]*' | cut -d'"' -f4)
echo ""
echo "Job ID: $JOB_ID"
echo ""

if [ -z "$JOB_ID" ]; then
  echo "Failed to create job"
  exit 1
fi

echo "Waiting 15 seconds..."
sleep 15

echo ""
echo "Final status:"
curl -s http://localhost:8080/api/v1/jobs/$JOB_ID -H "Authorization: Bearer $TOKEN"
