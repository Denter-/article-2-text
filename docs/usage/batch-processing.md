# Batch Processing Guide

Process multiple articles efficiently with batch extraction.

---

## Quick Start

```bash
# 1. Create URL list
echo "https://www.forentrepreneurs.com/saas-metrics-2/" > config/urls.txt
echo "https://www.forentrepreneurs.com/startup-killer/" >> config/urls.txt

# 2. Run batch extraction
python3 -m src.article_extractor --gemini -f config/urls.txt

# 3. Find results
ls results/
```

---

## Creating URL Lists

### Format

One URL per line in a text file:

```text
https://www.forentrepreneurs.com/saas-metrics-2/
https://www.forentrepreneurs.com/startup-killer/
https://www.forentrepreneurs.com/cash-flow-vs-profitability/
```

### File Location

Default: `config/urls.txt`
Custom: Any text file path

```bash
# Use default
python3 -m src.article_extractor --gemini -f config/urls.txt

# Use custom file
python3 -m src.article_extractor --gemini -f my_urls.txt
```

---

## Running Batch Jobs

### Method 1: Python Script

```bash
python3 -m src.article_extractor --gemini -f config/urls.txt
```

**Advantages:**
- Full error handling
- Progress tracking
- Summary report

### Method 2: Bash Script

```bash
./scripts/batch_extract.sh
```

**Advantages:**
- Simple one-command execution
- Reads from `config/urls.txt`
- Activates venv automatically

---

## Monitoring Progress

### Console Output

```
🚀 Processing 10 article(s)...
🤖 Using AI-powered image descriptions via Gemini Vision API

[1/10] Processing: https://example.com/article-1
------------------------------------------------------------
📥 Downloading article...
📝 Extracting metadata...
🖼️  Found 24 images
🤖 Processing image 1/24... ✅ Described (92 words)
🤖 Processing image 2/24... ⏭️  Skipped (UI element)
...
✅ Success! Created: Article_1_Title.md

[2/10] Processing: https://example.com/article-2
------------------------------------------------------------
...

📊 SUMMARY
============================================================
✅ Successful: 8
❌ Failed: 2
📁 Output directory: /path/to/results

✅ Successfully processed:
   • Article_1_Title.md
   • Article_2_Title.md
   ...

❌ Failed:
   • https://example.com/article-9 (HTTP 404)
   • https://example.com/article-10 (Connection timeout)
```

### Log Files

All processing details are logged to `logs/`:

```bash
# View latest log
ls -lt logs/
cat logs/extraction_2025-10-02_14-30-15.log
```

---

## Managing Output

### Default Structure

```
results/
├── Article_1_Title.md
├── Article_2_Title.md
├── Article_3_Title.md
└── ...
```

### Custom Output Directory

```bash
python3 -m src.article_extractor --gemini \
  -f config/urls.txt \
  -o results/my_batch
```

Output:
```
results/my_batch/
├── Article_1_Title.md
├── Article_2_Title.md
└── ...
```

### Organizing by Topic

```bash
# SaaS metrics articles
python3 -m src.article_extractor --gemini \
  -f config/saas_metrics_urls.txt \
  -o results/saas_metrics

# Marketing articles
python3 -m src.article_extractor --gemini \
  -f config/marketing_urls.txt \
  -o results/marketing
```

---

## Performance Considerations

### Processing Time

| Articles | Images (avg) | Time (AI) | Time (no AI) |
|----------|-------------|-----------|--------------|
| 1 | 24 | 1-2 min | 3 sec |
| 10 | 240 | 15-20 min | 30 sec |
| 50 | 1,200 | 75-100 min | 2.5 min |
| 100 | 2,400 | 2.5-3 hours | 5 min |

**Note:** Times vary based on:
- Network speed
- Article complexity
- Image count
- API response time

### Cost Estimation

With Gemini 2.5 Flash:

| Batch Size | Avg Images | Est. Cost |
|------------|-----------|-----------|
| 10 articles | ~240 | $2.50-5.00 |
| 50 articles | ~1,200 | $12-25 |
| 100 articles | ~2,400 | $25-50 |

**Calculate your cost:**
```
Total images × $0.01-0.02 per image = Estimated cost
```

### Rate Limiting

The tool includes automatic rate limiting:
- 3 seconds delay between image requests
- Automatic retry on rate limit errors
- Exponential backoff on failures

---

## Error Handling

### Automatic Recovery

The tool automatically:
- ✅ Continues on single article failure
- ✅ Retries failed API calls
- ✅ Logs all errors
- ✅ Provides summary of successes/failures

### Failed Articles

Check the summary for failed articles:

```
❌ Failed:
   • https://example.com/article-9 (HTTP 404)
   • https://example.com/article-10 (Connection timeout)
```

**Next steps:**
1. Check the URLs manually
2. Review the log file
3. Create a new list with failed URLs
4. Re-run extraction

### Resuming Failed Extractions

```bash
# 1. Extract failed URLs from summary
# (manually create new file with failed URLs)

# 2. Create failed_urls.txt
cat > config/failed_urls.txt << EOF
https://example.com/article-9
https://example.com/article-10
EOF

# 3. Retry
python3 -m src.article_extractor --gemini -f config/failed_urls.txt
```

---

## Best Practices

### 1. Test First

Always test with a small batch before running large jobs:

```bash
# Test with 2-3 URLs
python3 -m src.article_extractor --gemini -f config/test_urls.txt

# Review output
ls -lh results/

# If good, proceed with full batch
python3 -m src.article_extractor --gemini -f config/full_urls.txt
```

### 2. Organize by Topic

Keep URL lists organized:

```
config/
├── urls.txt                  # All URLs
├── saas_metrics_urls.txt    # SaaS metrics
├── marketing_urls.txt       # Marketing
└── finance_urls.txt         # Finance
```

### 3. Use Version Control

Track your URL lists:

```bash
git add config/urls.txt
git commit -m "Add 50 new article URLs"
```

### 4. Monitor Logs

Review logs periodically:

```bash
# Check for errors
grep "ERROR" logs/*.log

# Check for rate limiting
grep "rate limit" logs/*.log

# Check success rate
grep "Successfully processed" logs/*.log
```

### 5. Backup Results

Regularly backup extracted articles:

```bash
# Create backup
tar -czf results_backup_$(date +%Y%m%d).tar.gz results/

# Or use git
git add results/
git commit -m "Batch extraction complete"
```

---

## Advanced Usage

### Parallel Processing

For very large batches, split into chunks:

```bash
# Split URLs into chunks of 10
split -l 10 config/urls.txt config/batch_

# Process in parallel (different terminals)
python3 -m src.article_extractor --gemini -f config/batch_aa -o results/batch1
python3 -m src.article_extractor --gemini -f config/batch_ab -o results/batch2
python3 -m src.article_extractor --gemini -f config/batch_ac -o results/batch3
```

**Warning:** Watch for API rate limits!

### Scheduling

Schedule regular extractions with cron:

```bash
# Edit crontab
crontab -e

# Add: Run every Sunday at 2 AM
0 2 * * 0 cd /path/to/project && source venv/bin/activate && python3 -m src.article_extractor --gemini -f config/urls.txt
```

---

## Troubleshooting

### Issue: Batch Stops Midway

**Symptom:** Processing stops without completing all articles

**Possible causes:**
- Network timeout
- API rate limit exceeded
- System resource exhaustion

**Solutions:**
1. Check logs for error details
2. Resume from failed URLs
3. Reduce batch size
4. Increase delay between requests

### Issue: High API Costs

**Symptom:** Gemini API costs higher than expected

**Possible causes:**
- Many high-resolution images
- Repeated processing of same articles
- UI elements not filtered

**Solutions:**
1. Review image count before batch processing
2. Check output directory to avoid duplicates
3. Verify UI filtering is working

### Issue: Poor Description Quality

**Symptom:** AI descriptions are generic or incorrect

**Possible causes:**
- Poor context extraction
- Image quality issues
- Prompt needs tuning

**Solutions:**
1. Review [Validation Report](../technical/validation-report.md)
2. Check [Prompt Improvements](../technical/prompt-improvements.md)
3. Test with different articles

---

## Example Workflows

### Workflow 1: New Article Collection

```bash
# 1. Collect URLs
# (manually browse website and collect URLs)

# 2. Create URL list
cat > config/new_collection.txt << EOF
https://example.com/article-1
https://example.com/article-2
...
EOF

# 3. Test with one URL
python3 -m src.article_extractor --gemini https://example.com/article-1

# 4. Review output
cat results/Article_1_Title.md

# 5. If good, process full batch
python3 -m src.article_extractor --gemini \
  -f config/new_collection.txt \
  -o results/new_collection

# 6. Verify results
ls -lh results/new_collection/
```

### Workflow 2: Regular Updates

```bash
# 1. Update URL list with new articles
vim config/urls.txt

# 2. Run incremental extraction
./scripts/batch_extract.sh

# 3. Review new articles
ls -lt results/ | head -10

# 4. Commit results
git add results/
git commit -m "Add 5 new articles"
```

---

## Next Steps

- **Understand AI descriptions:** [Gemini Integration](gemini-integration.md)
- **Improve quality:** [Prompt Improvements](../technical/prompt-improvements.md)
- **Technical details:** [Architecture](../technical/architecture.md)

---

[← Back to Documentation Hub](../index.md) | [Main README](../../README.md)

