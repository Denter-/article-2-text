#!/bin/bash
# Quick test for Gemini Vision API
# Usage: ./quick_test.sh YOUR_API_KEY

# Get project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Try to load from .env
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

if [ -z "$1" ] && [ -z "$GEMINI_API_KEY" ]; then
    echo "Usage: $0 YOUR_API_KEY"
    echo ""
    echo "Or set environment variable:"
    echo "export GEMINI_API_KEY='your_key'"
    echo "./quick_test.sh"
    echo ""
    echo "Or add GEMINI_API_KEY to .env file"
    exit 1
fi

API_KEY="${1:-$GEMINI_API_KEY}"

echo "🧪 Quick Gemini API Test"
echo "========================"
echo ""
echo "Testing with a simple text-only request..."
echo ""

curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${API_KEY}" \
  -H 'Content-Type: application/json' \
  -d '{
    "contents": [{
      "parts":[{"text": "Hello! Please respond with: API is working correctly."}]
    }]
  }' | python3 -m json.tool

echo ""
echo "=================================================="
echo ""
if [ $? -eq 0 ]; then
    echo "✅ If you see a response above, your API key is working!"
    echo "✅ Now you can run: python3 -m tests.test_gemini_vision"
    echo "✅ Or extract an article: python3 -m src.article_extractor --gemini URL"
else
    echo "❌ Test failed. Check your API key."
fi
echo ""

