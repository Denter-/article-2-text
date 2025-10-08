# Python CLI Usage Guide

**Extract articles using the command-line interface**

---

## 🚀 Quick Start

### **Basic Extraction**
```bash
# Extract a single article
python src/article_extractor.py https://example.com/article

# With AI image descriptions
python src/article_extractor.py --gemini https://example.com/article
```

### **Output**
The system will create a Markdown file in the `results/` directory with:
- Clean article content
- Metadata (title, author, date)
- Image descriptions (if using `--gemini`)
- Source URL and extraction timestamp

---

## 📋 Command Reference

### **Basic Syntax**
```bash
python src/article_extractor.py [OPTIONS] URL
```

### **Options**

| Option | Description | Example |
|--------|-------------|---------|
| `URL` | Article URL to extract | `https://example.com/article` |
| `--gemini` | Enable AI image descriptions | `--gemini` |
| `-o`, `--output` | Output directory | `-o results/my_folder` |
| `-f`, `--file` | Extract from URL list | `-f config/urls.txt` |
| `--learn` | Learn new site configuration | `--learn` |
| `--force-renew` | Force re-learning site | `--force-renew` |
| `--browser` | Use browser for JavaScript sites | `--browser` |
| `-v`, `--verbose` | Verbose output | `-v` |
| `-h`, `--help` | Show help message | `-h` |

---

## 🎯 Common Use Cases

### **Single Article Extraction**
```bash
# Basic extraction
python src/article_extractor.py https://example.com/article

# With AI image descriptions
python src/article_extractor.py --gemini https://example.com/article

# Save to specific directory
python src/article_extractor.py -o results/research https://example.com/article
```

### **Batch Processing**
```bash
# Create URL list
echo "https://example.com/article1" > urls.txt
echo "https://example.com/article2" >> urls.txt

# Process all URLs
python src/article_extractor.py -f urls.txt

# With AI descriptions
python src/article_extractor.py --gemini -f urls.txt
```

### **Learning New Sites**
```bash
# Learn how to extract from a new site
python src/article_extractor.py --learn https://newsite.com/article

# Force re-learning (if extraction quality is poor)
python src/article_extractor.py --force-renew https://newsite.com/article
```

### **JavaScript-Heavy Sites**
```bash
# Use browser for dynamic content
python src/article_extractor.py --browser https://spa-site.com/article

# Combine with learning
python src/article_extractor.py --learn --browser https://spa-site.com/article
```

---

## 🧠 Site Learning Process

### **How It Works**
When you use `--learn` or `--force-renew`, the system:

1. **Downloads the page** - Gets the full HTML content
2. **Analyzes structure** - Uses AI to understand the page layout
3. **Identifies content** - Finds the main article container
4. **Detects noise** - Identifies navigation, ads, and other unwanted content
5. **Creates rules** - Generates extraction configuration
6. **Tests extraction** - Validates the rules work correctly
7. **Saves configuration** - Stores rules for future use

### **Learning Indicators**
```
🤖 LEARNING NEW SITE: newsite.com
📥 Downloading page...
🔍 Analyzing HTML structure...
🧠 Asking AI for extraction rules...
✅ Config received from AI
🔍 Testing extraction...
✅ Extraction successful: 2,847 characters
💾 Saving configuration...
✅ Site learned successfully!
```

### **When to Use Learning**
- **New site not working** - Extraction returns poor results
- **Site structure changed** - Previously working site now fails
- **Quality issues** - Content includes navigation or ads
- **First time using site** - No existing configuration

---

## 🎨 Output Format

### **Markdown Structure**
```markdown
# Article Title

**Author:** Author Name  
**Published:** 2025-01-02  
**Source:** [Original URL](https://example.com/article)  
**Extracted:** 2025-01-02 15:30:00  

---

## Article Content

The main article content goes here...

![Image Description](image-url.jpg)
*AI-generated description: A person working at a computer*

## More Content

Additional paragraphs and sections...
```

### **File Naming**
Files are named based on the article title:
- `Article_Title.md` - Clean title with underscores
- Special characters removed
- Length limited to 100 characters

---

## 🔧 Advanced Usage

### **Verbose Output**
```bash
# See detailed extraction process
python src/article_extractor.py -v https://example.com/article
```

### **Custom Output Directory**
```bash
# Save to specific folder
python src/article_extractor.py -o research/papers https://example.com/article
```

### **URL List Processing**
```bash
# Create URL list file
cat > urls.txt << EOF
https://example.com/article1
https://example.com/article2
https://example.com/article3
EOF

# Process all URLs
python src/article_extractor.py -f urls.txt
```

### **Combining Options**
```bash
# Learn new site with browser and AI descriptions
python src/article_extractor.py --learn --browser --gemini https://newsite.com/article

# Batch process with AI descriptions
python src/article_extractor.py --gemini -f urls.txt -o results/ai_processed
```

---

## 🐛 Troubleshooting

### **Common Issues**

#### **"Site not supported" Error**
```bash
# Learn the site first
python src/article_extractor.py --learn https://newsite.com/article
```

#### **Poor extraction quality**
```bash
# Force re-learning
python src.article_extractor.py --force-renew https://site.com/article
```

#### **JavaScript content missing**
```bash
# Use browser mode
python src/article_extractor.py --browser https://spa-site.com/article
```

#### **AI descriptions not working**
```bash
# Check API key is set
echo $GEMINI_API_KEY

# Test with verbose output
python src/article_extractor.py --gemini -v https://example.com/article
```

### **Quality Issues**

#### **Navigation in content**
- Use `--force-renew` to re-learn the site
- The system will identify and remove navigation patterns

#### **Incomplete articles**
- Check if the site requires browser mode (`--browser`)
- Some sites load content dynamically

#### **Missing images**
- Use `--browser` for JavaScript-rendered images
- Check if images are behind authentication

---

## 📊 Performance Tips

### **Faster Extraction**
- Use sites that are already learned
- Avoid `--learn` unless necessary
- Use `--browser` only for JavaScript-heavy sites

### **Batch Processing**
- Process URLs in smaller batches (10-20 at a time)
- Use `--gemini` only when needed (adds processing time)
- Monitor disk space for large batches

### **Memory Usage**
- Close other applications during large batches
- Use `--browser` sparingly (uses more memory)
- Consider processing during off-peak hours

---

## 🎯 Best Practices

### **For Research**
```bash
# Extract with AI descriptions for analysis
python src/article_extractor.py --gemini -o research/ai_articles https://example.com/article
```

### **For Content Processing**
```bash
# Batch process without AI (faster)
python src/article_extractor.py -f urls.txt -o content/processed
```

### **For Site Learning**
```bash
# Learn multiple sites systematically
python src/article_extractor.py --learn https://site1.com/article
python src.article_extractor.py --learn https://site2.com/article
```

---

## 📚 Next Steps

- **[Batch Processing](batch-processing.md)** - Process multiple articles efficiently
- **[System Architecture](../technical/architecture.md)** - Understand how it works
- **[API Reference](../usage/api-reference.md)** - Use the REST API for automation

---

**Need help?** Check the [troubleshooting section](#troubleshooting) or see [System Overview](../README.md) for more details.



