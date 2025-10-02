# Gemini Vision API Setup Guide

## Quick Setup (3 methods)

### Method 1: Environment Variable (Recommended)
```bash
export GEMINI_API_KEY='your_actual_api_key_here'
python3 test_gemini_vision.py
```

### Method 2: Config File
```bash
# Create config.json from template
cp config.json.template config.json

# Edit config.json and add your API key
nano config.json  # or use any editor

# Run test
python3 test_gemini_vision.py
```

### Method 3: Direct in Script
Edit `test_gemini_vision.py` and add at the top:
```python
API_KEY = "your_actual_api_key_here"
```

## Getting Your API Key

1. Go to: https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key
4. Use one of the methods above

## Running the Test

```bash
# Make executable
chmod +x test_gemini_vision.py

# Run test
python3 test_gemini_vision.py
```

## What the Test Does

1. Downloads 3 test images from the SaaS Metrics article
2. Sends each to Gemini Vision API with context
3. Gets AI-generated descriptions
4. Shows results and saves to `gemini_test_results.json`

## Expected Output

```
🧪 Gemini Vision API - Image Description Test
============================================================
✓ API key loaded

####################################################
# TEST 1/3: Chart 1: SaaS P&L Trough
####################################################

Testing image: https://i0.wp.com/www.forentrepreneurs.com...
============================================================
📥 Downloading image...
✓ Downloaded: 45,234 bytes
🤖 Calling Gemini Vision API...

────────────────────────────────────────────────────────────
📝 GENERATED DESCRIPTION:
────────────────────────────────────────────────────────────
[AI-generated description here]
────────────────────────────────────────────────────────────
```

## Troubleshooting

### "API key not found"
- Make sure you've set the API key using one of the 3 methods
- Check that there are no extra spaces or quotes

### "API Error: 403"
- Your API key may be invalid
- Check if you need to enable the Gemini API in Google Cloud Console

### "Failed to download image"
- Check your internet connection
- The image URL might be temporarily unavailable

### "Response format unexpected"
- The API might have changed
- Check Google's Gemini API documentation for updates

## API Limits

Free tier:
- 15 requests per minute
- 1500 requests per day
- Rate limiting built into the test script

## Next Steps

Once the test works:
1. Review the generated descriptions
2. Adjust the system prompt if needed
3. Integrate into `article_extractor.py`

## System Prompt Tuning

Edit the `system_prompt` in `test_gemini_vision.py` to customize:
- Description style
- Level of detail
- Focus areas
- Output format

Current prompt emphasizes:
- Identifying visualization type
- Explaining data/concepts
- Key insights and patterns
- Accessibility for text-to-speech

## Cost Estimate

Gemini 1.5 Flash pricing (as of 2024):
- Input: $0.00001875 per 1K characters
- Output: $0.000075 per 1K characters

For 100 images with context:
- ~$0.50-1.00 total (very affordable!)

Much cheaper than GPT-4 Vision.

