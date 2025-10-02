# Quick Start Guide

## 🚀 Get Started in 3 Steps

### Option 1: Single Article

```bash
python3 article_extractor.py https://www.forentrepreneurs.com/startup-killer/
```

### Option 2: Multiple Articles

```bash
# 1. Edit forentrepreneurs_urls.txt - uncomment URLs you want
# 2. Run batch extraction
./batch_extract.sh

# Or directly with Python
python3 article_extractor.py -f forentrepreneurs_urls.txt
```

### Option 3: Manual URLs

```bash
python3 article_extractor.py \
  https://www.forentrepreneurs.com/article1/ \
  https://www.forentrepreneurs.com/article2/
```

## ⚡ What Happens

1. **Downloads** article HTML
2. **Extracts** content, metadata, and images
3. **Converts** to clean Markdown
4. **Replaces** all images with text descriptions
5. **Saves** to `.md` file

## 📂 Files Created

Each article becomes: `Article_Title.md`

Example: `Startup_Killer_The_Cost_of_Customer_Acquisition.md`

## 💡 Tips

### Test First
Start with 1-2 articles to verify output quality:
```bash
python3 article_extractor.py https://www.forentrepreneurs.com/product-market-fit/
```

### Review Output
Always check the generated files, especially image descriptions.

### Enhance Descriptions
For better image descriptions, manually enhance them based on:
- Context provided in the description
- Original image link included
- Your knowledge of the topic

### Batch Process
Once satisfied, uncomment all URLs in `forentrepreneurs_urls.txt` and run:
```bash
./batch_extract.sh
```

## 🛠️ Customization

### Add More URLs

Edit `forentrepreneurs_urls.txt`:
```
# Just add URLs, one per line
https://www.forentrepreneurs.com/your-article/
```

### Change Output Directory

```bash
python3 article_extractor.py -o ./my_articles -f forentrepreneurs_urls.txt
```

### Improve Image Descriptions

Edit `article_extractor.py`, find the `generate_image_description()` method and add custom logic.

## 🔍 Verify Installation

Check if everything needed is available:

```bash
# Check Python
python3 --version  # Should show Python 3.x

# Check curl
curl --version  # Should show curl version

# Test the script
python3 article_extractor.py --help  # Should show help message
```

## 📖 Example Workflow

```bash
# 1. Check what you have
cat forentrepreneurs_urls.txt

# 2. Test with one article
python3 article_extractor.py https://www.forentrepreneurs.com/product-market-fit/

# 3. Review the output
ls -lh Product*.md

# 4. If satisfied, process all
./batch_extract.sh

# 5. Review results
ls -lh *.md
```

## ❓ Troubleshooting

**Script won't run?**
```bash
chmod +x article_extractor.py batch_extract.sh
```

**No output file?**
- Check error messages
- Article structure may be different
- URL may be incorrect

**Poor image descriptions?**
- This is expected - they're auto-generated from context
- Manually enhance important descriptions
- Reference original images using provided links

## 📚 More Help

See `README.md` for comprehensive documentation.

## 🎯 Real World Example

What was done for SaaS_Metrics_2.0.md:
1. Extracted article (9,900 words)
2. Identified 24 images
3. Created detailed descriptions for each
4. Generated clean, accessible Markdown

You can do the same automatically for most articles, then enhance manually as needed!

