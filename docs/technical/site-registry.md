# Self-Learning Site Registry

**Automatically learns how to extract articles from any website using AI.**

---

## Overview

The Site Registry is a self-learning system that uses Google Gemini to analyze websites and create extraction rules automatically. Once learned, these rules are saved and reused for all future articles from that domain.

### Key Benefits

- 🤖 **Automatic Learning** - AI analyzes HTML and creates extraction rules
- 💰 **Cost Efficient** - Learn once ($0.01-0.05), extract forever (free)
- ✅ **Self-Validating** - AI validates its own work before saving
- 🔄 **Iterative** - Refines rules up to 3 times for perfection
- 🔧 **Force Renew** - Re-learn when sites change structure

---

## Architecture

```mermaid
flowchart TD
    A[User Request: Extract Article] --> B{Domain Config Exists?}
    B -->|Yes| C[Load config/sites/domain.yaml]
    B -->|No| D[🧠 LEARNING MODE]
    
    C --> E[Extract Using Config]
    
    D --> F[Send HTML to Gemini<br/>'Analyze structure']
    F --> G[Receive YAML Config]
    G --> H[Apply Config & Extract]
    H --> I[Send to Gemini<br/>'Validate quality']
    
    I --> J{Valid?}
    J -->|APPROVE| K[💾 Save Config]
    J -->|Issues| L{Iterations < 3?}
    L -->|Yes| M[Request Better Config]
    M --> H
    L -->|No| N[❌ Failed]
    
    K --> E
    E --> O[✅ Article Extracted]
```

---

## Configuration Format

### YAML Structure

```yaml
domain: example.com
learned_at: "2025-10-02T14:30:00Z"

extraction:
  # Main article content
  article_content:
    selector: "article"          # CSS selector
    fallback: "main"              # Fallback option
  
  # Metadata
  title:
    og_meta: "og:title"
    fallback_selector: "h1"
  
  author:
    json_ld: "author.name"
    fallback_selector: ".author"
  
  date_published:
    json_ld: "datePublished"

notes: |
  Site uses standard semantic HTML.
  Tested on 3 articles successfully.
```

### Location

```
config/sites/
├── _template.yaml           # Template reference
├── forentrepreneurs.com.yaml
├── example.com.yaml
└── newsite.com.yaml
```

---

## The Learning Process

```mermaid
sequenceDiagram
    participant U as User
    participant S as System
    participant G as Gemini AI
    
    U->>S: Extract article from newsite.com
    S->>S: Check config/sites/newsite.com.yaml
    
    Note over S: Config not found
    
    S->>G: Analyze HTML structure
    G->>S: Return extraction selectors (YAML)
    
    S->>S: Apply selectors & extract content
    
    S->>G: Validate extraction<br/>(HTML + Extracted Content)
    
    alt Validation Success
        G->>S: "APPROVE"
        S->>S: Save config to disk
        S->>U: ✅ Article extracted
    else Validation Failed
        G->>S: "Issues: X, Y, Z"
        Note over S: Iteration 2/3
        S->>G: Request improved selectors
        G->>S: Return better selectors
        S->>S: Apply & validate again
    end
```

### Iteration Loop (Max 3 Attempts)

1. **Attempt 1**: Initial learning from HTML
2. **Attempt 2**: Refinement based on validation feedback
3. **Attempt 3**: Final attempt with feedback
4. **Success**: ~90% on standard article sites

---

## Usage

### Automatic Learning

```bash
# First time visiting a new site
python3 -m src.article_extractor --gemini https://newsite.com/article

# Output:
# 🧠 Learning extraction rules for newsite.com...
#    Analyzing HTML structure with AI...
#    Iteration 1/3
#    ✓ Received extraction config from AI
#    🔍 Validating extraction quality...
#    ✅ Extraction validated successfully!
#    💾 Saved config for newsite.com
# ✅ Success! Created: Article_Title.md

# Future visits (instant, free)
python3 -m src.article_extractor --gemini https://newsite.com/article-2
# ✓ Loaded config for newsite.com
# ✅ Success! Created: Article_2_Title.md
```

### Force Re-learning

```bash
# Site structure changed? Re-learn:
python3 -m src.article_extractor --gemini --force-renew https://site.com/article
```

### Manual Config Review

```bash
# View learned configuration
cat config/sites/example.com.yaml

# Edit if needed
vim config/sites/example.com.yaml

# Commit to share with team
git add config/sites/example.com.yaml
git commit -m "Add extraction config for example.com"
```

---

## Extraction Methods

The system supports two approaches:

### 1. CSS Selectors (Preferred)

```yaml
extraction:
  article_content:
    selector: "article.post-content"
    fallback: "div.entry-content"
```

Uses BeautifulSoup's `select_one()` method.

### 2. Pattern Matching (Fallback)

```yaml
content_pattern:
  start_marker: "<h1[^>]*>"
  end_marker: "(?=<footer|<div[^>]*class=\"comments\")"
```

Uses regex for complex cases where selectors fail.

---

## Cost Analysis

### Learning Phase (One-time per site)

```mermaid
graph LR
    A[New Site] -->|2-6 API calls| B[$0.01-0.05]
    B --> C[Config Saved]
    C --> D[All Future Extractions: FREE]
```

**Per site:**
- Learning: 1-3 API calls
- Validation: 1-3 API calls
- **Total: $0.01-0.05 one-time**

### Extraction Phase (After Learning)

**Cost: $0.00** - Uses saved config, no API calls

### Comparison

| Scenario | Without Registry | With Registry | Savings |
|----------|------------------|---------------|---------|
| 1 article (new site) | $0.50 | $0.50 | 0% |
| 10 articles (same site) | $5.00 | $0.53 | 89% |
| 100 articles (same site) | $50.00 | $0.55 | 99% |
| 100 articles (10 sites) | $50.00 | $1.00 | 98% |

---

## Implementation

### Core Class: `SiteRegistry`

```python
from site_registry import SiteRegistry

# Initialize
registry = SiteRegistry(config_dir="config/sites", use_gemini=True)

# Extract domain
domain = registry.get_domain_from_url(url)

# Try to load existing config
config = registry.load_config(domain)

if not config:
    # Learn from HTML
    success, config, error = registry.learn_from_html(url, html, force=False)
    
if config:
    # Extract using config
    content = registry.extract_with_config(html, config)
```

### Key Methods

```python
registry.load_config(domain)                 # Load YAML config
registry.save_config(domain, config)         # Save YAML config
registry.extract_with_config(html, config)   # Apply extraction rules
registry.learn_from_html(url, html, force)   # AI learning (main method)
```

---

## AI Prompts

### Learning Prompt

```
You are an expert at analyzing website HTML structure.

Your task: Provide CSS selectors to extract MAIN ARTICLE CONTENT.

IMPORTANT:
- Extract ONLY article content, not navigation/sidebars/ads
- Provide CSS selectors for BeautifulSoup
- Include fallback options

Return as YAML: [structure shown]
```

### Validation Prompt

```
You are validating article extraction quality.

Check:
1. Does extracted content include FULL article?
2. Does it EXCLUDE navigation/sidebars/ads/comments?
3. Is it clean and appropriate?

Respond:
- If good: "APPROVE"
- If issues: List specific problems
```

---

## Best Practices

### ✅ Do This

```bash
# Let it learn automatically on first encounter
python3 -m src.article_extractor --gemini https://newsite.com/article

# Test with 2-3 more articles to verify
python3 -m src.article_extractor --gemini https://newsite.com/article-2
python3 -m src.article_extractor --gemini https://newsite.com/article-3

# Commit working configs
git add config/sites/newsite.com.yaml
git commit -m "Add config for newsite.com"
```

### ❌ Don't Do This

```bash
# Don't manually create configs unless you're an expert
# Don't skip testing after learning
# Don't ignore failed validations
```

---

## Troubleshooting

### Learning Failed After 3 Attempts

**Possible causes:**
- Site is JavaScript-rendered (SPA)
- Requires authentication
- Unusual HTML structure

**Solutions:**
1. Try different article from same site
2. Check: `curl -s https://site.com/article | grep "text from article"`
3. Manually create config if necessary

### Config Exists But Extraction Poor

```bash
# Force re-learning
python3 -m src.article_extractor --gemini --force-renew https://site.com/article
```

### Extraction Includes Navigation/Sidebar

Check config and refine selector:
```yaml
# Change from:
selector: "main"

# To more specific:
selector: "main article.post-content"
```

---

## Limitations

### What It Can't Handle

❌ **JavaScript SPAs** - Content loaded via JS after page load  
❌ **Authentication Required** - Sites behind login  
❌ **Highly Dynamic Content** - Content that changes structure frequently

### Success Rate

✅ **90%+** - Standard article sites (WordPress, static blogs, semantic HTML)  
⚠️ **50%** - News sites with complex layouts  
❌ **10%** - SPAs, paywalled content

---

## Future Enhancements

1. **Automated Re-validation** - Monthly checks of saved configs
2. **Community Config Sharing** - Central repository of pre-made configs
3. **Confidence Scoring** - Track success rate per config
4. **Version History** - Keep config history, rollback if needed

---

## Quick Reference

```bash
# First article from new site (learns automatically)
python3 -m src.article_extractor --gemini https://newsite.com/article

# Subsequent articles (instant, free)
python3 -m src.article_extractor --gemini https://newsite.com/article-2

# Force re-learning
python3 -m src.article_extractor --gemini --force-renew https://site.com/article

# View learned config
cat config/sites/newsite.com.yaml

# Test registry module
python3 src/site_registry.py
```

---

## Summary

The Self-Learning Site Registry transforms article extraction from manual, per-site coding into an automated, AI-powered system that:

- ✅ Learns extraction rules automatically
- ✅ Validates its own work before saving
- ✅ Saves 99% on costs for repeated extractions
- ✅ Works with thousands of sites
- ✅ Re-learns when sites change

**One-time learning, infinite reuse.**

---

## Related Documentation

- [Site Compatibility Guide](site-compatibility.md)
- [Architecture Overview](architecture.md)
- [Gemini Integration](../usage/gemini-integration.md)

---

[← Back to Documentation Hub](../index.md)

