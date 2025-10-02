# Installation Guide

Complete installation instructions for the Article Extractor with AI Image Descriptions.

---

## System Requirements

- **Python**: 3.8 or higher
- **Operating System**: Linux, macOS, or Windows (WSL recommended)
- **Disk Space**: ~500MB (for Playwright browser)
- **Internet**: Required for API calls and article downloads

---

## Step-by-Step Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd article-2-text
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv

# Activate on Linux/Mac:
source venv/bin/activate

# Activate on Windows:
venv\Scripts\activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `google-generativeai` - Gemini AI API
- `pillow` - Image processing
- `playwright` - Headless browser
- `beautifulsoup4` - HTML parsing
- `pyyaml` - Config management
- And other dependencies

### 4. Install Playwright Browsers

**Required for JavaScript-rendered sites (HBR, Medium, etc.)**

```bash
playwright install chromium
```

This downloads Chromium (~200MB) for headless browser rendering.

**Note**: You only need to run this once per system.

---

## Configure Gemini API Key

Choose one of these methods:

### Option 1: .env File (Recommended)

```bash
cp .env.example .env
```

Edit `.env` and add your API key:
```
GEMINI_API_KEY=your_actual_key_here
```

### Option 2: Config File

```bash
cp config/config.json.example config/config.json
```

Edit `config/config.json` and add your API key.

### Option 3: Environment Variable

```bash
export GEMINI_API_KEY='your_api_key_here'
```

**Get your free API key:** https://makersuite.google.com/app/apikey

---

## Verify Installation

Test with a simple article:

```bash
python3 -m src.article_extractor --gemini https://www.forentrepreneurs.com/saas-metrics-2/
```

Expected output:
```
✓ Gemini learning enabled (Flash model)
📥 Downloading article...
✓ Downloaded successfully (256,789 bytes)
🧠 Learning extraction rules for forentrepreneurs.com...
   Iteration 1/6
   ✅ Extraction validated successfully!
🤖 Processing 13 images in parallel...
   ✓ Processed 13/13 images in 42s
✅ Success! Created: results/SaaS_Metrics_2.md
```

---

## Troubleshooting

### Playwright Browser Not Found

```bash
# Install Chromium browser
playwright install chromium

# Or install all browsers (not necessary)
playwright install
```

### Import Errors

```bash
# Make sure you're in the virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### API Key Errors

- Verify the `.env` file is in the project root directory
- Check that the API key has no extra spaces or quotes
- Confirm the key is valid at https://makersuite.google.com/app/apikey

### Permission Errors on Windows

Run as administrator or use WSL (Windows Subsystem for Linux).

---

## Next Steps

- **[Quick Start Guide](quickstart.md)** - Extract your first article
- **[Gemini Setup Guide](setup-gemini.md)** - Detailed API configuration
- **[Basic Usage](../usage/basic-usage.md)** - Command-line options

---

[← Back to Documentation Hub](../index.md)

