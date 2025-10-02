#!/bin/bash
# Convenience script for batch processing ForEntrepreneurs.com articles

set -e

# Get project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "=================================================="
echo "  ForEntrepreneurs Article Batch Extractor"
echo "=================================================="
echo ""

# Check if URLs file exists
if [ ! -f "config/urls.txt" ]; then
    echo "❌ Error: config/urls.txt not found"
    echo "   Create this file with URLs (one per line)"
    echo ""
    echo "   Example:"
    echo "   https://www.forentrepreneurs.com/saas-metrics-2/"
    echo "   https://www.forentrepreneurs.com/startup-killer/"
    exit 1
fi

# Count non-comment, non-empty lines
URL_COUNT=$(grep -v '^#' config/urls.txt | grep -v '^$' | wc -l)

if [ "$URL_COUNT" -eq 0 ]; then
    echo "❌ Error: No URLs found in config/urls.txt"
    echo "   Add URLs (one per line)"
    exit 1
fi

echo "📋 Found $URL_COUNT URL(s) to process"
echo ""

# Ask for confirmation
read -p "🤔 Proceed with extraction? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "🚀 Starting batch extraction with AI descriptions..."
echo ""

# Activate venv if not already activated
if [ -z "$VIRTUAL_ENV" ] && [ -d "venv" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
fi

# Run the extractor with Gemini
python3 -m src.article_extractor --gemini -f config/urls.txt

echo ""
echo "=================================================="
echo "  ✅ Batch extraction complete!"
echo "=================================================="
echo ""
echo "📁 Check results/ directory for generated .md files"

