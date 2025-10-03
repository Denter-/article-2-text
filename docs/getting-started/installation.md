# Quick Test Instructions

## 1. Install Dependencies

```bash
# Activate venv if you have one
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

## 2. Set API Key

Create a `.env` file:
```bash
cp .env.example .env
```

Edit `.env` and add your actual Gemini API key:
```
GEMINI_API_KEY=your_actual_key_here
```

Get your key from: https://makersuite.google.com/app/apikey

## 3. Run Test

```bash
python3 test_gemini_vision_v2.py
```

## What It Does

1. Downloads 4 test images from the SaaS Metrics article
2. Sends each to Gemini Vision API with article context
3. Displays AI-generated descriptions
4. Saves results to `gemini_test_results.json`
5. Keeps images in `/tmp/gemini_test_images/` for your review

## Expected Runtime

- About 30-60 seconds total
- 3-second pause between images (rate limiting)
- Cost: ~$0.04-0.08 total

## After Running

1. Review the printed descriptions
2. Check the downloaded images in `/tmp/gemini_test_images/`
3. Verify descriptions accurately capture what's shown
4. Check `gemini_test_results.json` for saved output

## Troubleshooting

**Import Error:**
```
pip install google-generativeai pillow python-dotenv
```

**API Key Error:**
- Make sure `.env` file exists in project root
- Check that API key has no extra spaces/quotes
- Verify key is valid at https://makersuite.google.com/app/apikey

**Download Errors:**
- Check internet connection
- Images might be temporarily unavailable

