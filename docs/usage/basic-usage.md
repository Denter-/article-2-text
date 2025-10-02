# Basic Usage Guide

Learn how to extract articles using the Article Extractor with AI Image Descriptions.

---

## Prerequisites

Before starting, ensure you have:
- ✅ Installed the tool (see [Installation Guide](../getting-started/installation.md))
- ✅ Activated the virtual environment
- ✅ (Optional) Configured Gemini API key for AI descriptions

---

## Command-Line Syntax

```bash
python3 -m src.article_extractor [OPTIONS] URL
```

### Basic Options

| Option | Description | Example |
|--------|-------------|---------|
| `URL` | Article URL to extract | `https://example.com/article` |
| `--gemini` | Enable AI image descriptions | `--gemini` |
| `-o`, `--output` | Output directory | `-o results/my_folder` |
| `-f`, `--file` | Extract from URL list | `-f config/urls.txt` |
| `-h`, `--help` | Show help message | `-h` |

---

## Basic Extraction

### Without AI (Free, Fast)

```bash
python3 -m src.article_extractor https://www.forentrepreneurs.com/saas-metrics-2/
```

**Output:**
```
📝 Using context-based image descriptions (free)
✅ Success! Created: SaaS_Metrics_2_0_For_Entrepreneurs.md
```

**Image descriptions:** Basic context-based placeholders
**Cost:** Free
**Speed:** Very fast (~2-3 seconds)

---

### With AI Descriptions (Recommended)

```bash
python3 -m src.article_extractor --gemini https://www.forentrepreneurs.com/saas-metrics-2/
```

**Output:**
```
🤖 Using AI-powered image descriptions via Gemini Vision API
🖼️  Processing image 1/24...
🖼️  Processing image 2/24...
...
✅ Success! Created: SaaS_Metrics_2_0_For_Entrepreneurs.md
```

**Image descriptions:** Detailed, context-aware AI descriptions
**Cost:** ~$0.25-0.50 per article
**Speed:** ~1-2 minutes (depends on image count)

---

## Understanding the Output

### Output Location

By default, articles are saved to:
```
results/Article_Title_Sanitized.md
```

Example:
```
results/SaaS_Metrics_2_0_For_Entrepreneurs.md
```

### Custom Output Directory

```bash
python3 -m src.article_extractor --gemini \
  --output results/my_collection \
  https://example.com/article
```

---

## Processing Status

### Progress Indicators

```
📥 Downloading article from https://example.com/article...
📝 Extracting metadata...
📄 Extracting article content...
🖼️  Extracting images...
   Found 24 images
🔄 Converting to Markdown...
🤖 Processing image 1/24...
   ✅ Image 1: Described (85 words)
🤖 Processing image 2/24...
   ⏭️  Image 2: Skipped (UI element)
...
💾 Creating Markdown file...
✅ Success! Created: Article_Title.md
```

### Success Summary

```
📊 SUMMARY
============================================================
✅ Successful: 1
❌ Failed: 0
📁 Output directory: /path/to/results
✅ Successfully processed:
   • Article_Title.md
```

---

## Working with Images

### AI-Powered Descriptions

When using `--gemini`, the tool:

1. **Analyzes each image** with Gemini Vision API
2. **Provides context** (surrounding text)
3. **Filters UI elements** (logos, buttons, navigation)
4. **Generates detailed descriptions** for charts, graphs, diagrams

**Example AI description:**

```markdown
**[AI-Generated Image Description 5/24]**

Line Graph: Monthly Recurring Revenue (MRR) Growth

This line graph illustrates MRR growth over 24 months across three 
pricing scenarios: $50/month (blue line), $100/month (orange line), 
and $150/month (green line). All three curves start at $0 and show 
exponential growth patterns. The $150 pricing achieves $36,000 MRR 
by month 24, while $50 pricing reaches $12,000...
```

### Context-Based Descriptions

Without `--gemini`, the tool uses surrounding text:

```markdown
**[Context-based Image Description]**

*This image appears between sections discussing "MRR Growth" and 
"Customer Acquisition". It likely visualizes data or concepts 
related to these topics.*
```

---

## Error Handling

### Common Errors

#### 1. URL Not Accessible

```
❌ Failed to download article from https://example.com/article
Error: HTTP 404 Not Found
```

**Solution:** Check the URL and try again

#### 2. API Key Not Found

```
⚠️  Warning: GEMINI_API_KEY not found in config or environment
📝 Using context-based image descriptions (free)
```

**Solution:** See [Gemini API Setup](../getting-started/setup-gemini.md)

#### 3. Rate Limit Exceeded

```
❌ Gemini API error for image 15: Rate limit exceeded
```

**Solution:** The tool automatically retries with delays. For large batches, consider increasing delays in the code.

#### 4. Network Timeout

```
❌ Failed to download image: Connection timeout
```

**Solution:** Check your internet connection. The tool will continue with other images.

---

## Output Format

### Markdown Structure

```markdown
# Article Title

**Author:** John Doe
**Published:** January 15, 2024
**Source:** https://example.com/article

---

## Section 1

Content here...

**[AI-Generated Image Description 1/24]**

Detailed image description...

More content...

## Section 2

...
```

### Metadata

Each article includes:
- Title
- Author (if available)
- Publication date
- Source URL
- Word count
- Image count

---

## Tips for Best Results

### 1. Use AI Descriptions for Visual Content

Articles with charts, graphs, or diagrams benefit most from AI descriptions.

```bash
# Good use case: Article with 20+ charts
python3 -m src.article_extractor --gemini https://example.com/charts-article

# Less useful: Text-only article with 2 logo images
python3 -m src.article_extractor https://example.com/text-article
```

### 2. Check Output Quality

Always review the first few extractions to ensure quality meets your needs.

```bash
# Extract one article first
python3 -m src.article_extractor --gemini https://example.com/article

# Review the output
cat results/Article_Title.md

# If good, proceed with batch processing
```

### 3. Monitor Costs

Track your API usage, especially for large batches.

```bash
# Estimate: 24 images × $0.01-0.02 per image = $0.24-0.48
python3 -m src.article_extractor --gemini https://example.com/article
```

---

## Next Steps

- **Process multiple articles:** [Batch Processing Guide](batch-processing.md)
- **Understand AI descriptions:** [Gemini Integration](gemini-integration.md)
- **Technical details:** [Architecture](../technical/architecture.md)

---

[← Back to Documentation Hub](../index.md) | [Main README](../../README.md)

