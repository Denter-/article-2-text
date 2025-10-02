#!/usr/bin/env python3
"""
Site Registry with LLM-powered learning
Automatically learns how to extract articles from new sites
"""

import os
import yaml
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime
from bs4 import BeautifulSoup

# Optional Gemini support
GEMINI_AVAILABLE = False
try:
    import google.generativeai as genai
    from dotenv import load_dotenv
    load_dotenv()
    GEMINI_AVAILABLE = True
except ImportError:
    pass


class SiteRegistry:
    """Manages site-specific extraction configurations with LLM learning"""
    
    def __init__(self, config_dir="config/sites", use_gemini=True):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.use_gemini = use_gemini and GEMINI_AVAILABLE
        self.gemini_model = None
        
        if self.use_gemini:
            api_key = os.getenv('GEMINI_API_KEY')
            if api_key:
                try:
                    genai.configure(api_key=api_key)
                    self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')
                    print("✓ Gemini learning enabled")
                except Exception as e:
                    print(f"⚠️  Gemini init failed: {e}")
                    self.use_gemini = False
    
    def get_domain_from_url(self, url):
        """Extract domain from URL"""
        parsed = urlparse(url)
        domain = parsed.netloc
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    
    def get_config_path(self, domain):
        """Get path to config file for domain"""
        return self.config_dir / f"{domain}.yaml"
    
    def load_config(self, domain):
        """Load site configuration from YAML"""
        config_path = self.get_config_path(domain)
        
        if not config_path.exists():
            return None
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        print(f"✓ Loaded config for {domain}")
        return config
    
    def save_config(self, domain, config):
        """Save site configuration to YAML"""
        config_path = self.get_config_path(domain)
        
        # Add timestamp
        config['learned_at'] = datetime.now().isoformat()
        
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        print(f"💾 Saved config for {domain}")
    
    def extract_with_config(self, html_content, config):
        """Extract article content using site config"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Try CSS selector method first
        extraction = config.get('extraction', {})
        article_config = extraction.get('article_content', {})
        
        # Try primary selector
        selector = article_config.get('selector')
        if selector:
            element = soup.select_one(selector)
            if element:
                return str(element)
        
        # Try fallback selector
        fallback = article_config.get('fallback')
        if fallback:
            element = soup.select_one(fallback)
            if element:
                return str(element)
        
        # Try pattern-based extraction if defined
        content_pattern = config.get('content_pattern')
        if content_pattern:
            start_marker = content_pattern.get('start_marker')
            end_marker = content_pattern.get('end_marker')
            
            if start_marker and end_marker:
                pattern = f"{start_marker}(.*?){end_marker}"
                match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
                if match:
                    return match.group(1)
        
        return None
    
    def learn_from_html(self, url, html_content, force=False):
        """
        Learn extraction rules from HTML using Gemini.
        Returns (success, config, error_message)
        """
        domain = self.get_domain_from_url(url)
        
        # Check if config exists
        if not force:
            existing_config = self.load_config(domain)
            if existing_config:
                print(f"✓ Config exists for {domain} (use --force-renew to recreate)")
                return True, existing_config, None
        
        if not self.use_gemini:
            return False, None, "Gemini not available - cannot learn new site"
        
        print(f"\n🧠 Learning extraction rules for {domain}...")
        print("   Analyzing HTML structure with AI...")
        
        # Ask Gemini to analyze the site
        max_iterations = 3
        for iteration in range(max_iterations):
            print(f"\n   Iteration {iteration + 1}/{max_iterations}")
            
            # First iteration: learn extraction rules
            if iteration == 0:
                config = self._ask_gemini_for_config(html_content, domain)
                if not config:
                    return False, None, "Failed to get config from Gemini"
            
            # Extract content using learned rules
            extracted_content = self.extract_with_config(html_content, config)
            
            if not extracted_content:
                print("   ❌ Extraction failed with suggested rules")
                if iteration < max_iterations - 1:
                    print("   🔄 Asking AI for better rules...")
                    config = self._ask_gemini_for_better_config(
                        html_content, domain, config, "Extraction returned nothing"
                    )
                continue
            
            # Validate extraction
            print("   🔍 Validating extraction quality...")
            is_valid, feedback = self._validate_extraction(
                html_content, extracted_content
            )
            
            if is_valid:
                print("   ✅ Extraction validated successfully!")
                self.save_config(domain, config)
                return True, config, None
            else:
                print(f"   ⚠️  Validation feedback: {feedback}")
                if iteration < max_iterations - 1:
                    print("   🔄 Refining extraction rules...")
                    config = self._ask_gemini_for_better_config(
                        html_content, domain, config, feedback
                    )
        
        # Failed after max iterations
        return False, None, f"Failed to learn valid rules after {max_iterations} attempts"
    
    def _ask_gemini_for_config(self, html_content, domain):
        """Ask Gemini to suggest extraction rules"""
        # Truncate HTML for cost efficiency (keep first 15000 chars - should include full article)
        html_sample = html_content[:15000]
        
        system_prompt = """You are an expert at analyzing website HTML structure and creating extraction rules.

Your task: Analyze the HTML and provide CSS selectors or patterns to extract the MAIN ARTICLE CONTENT.

IMPORTANT:
- Extract ONLY the article text content, not navigation, sidebars, ads, comments
- Provide CSS selectors that BeautifulSoup can use
- Include fallback options
- Be specific enough to avoid extracting non-content

Return your answer as valid YAML in this EXACT format:

```yaml
domain: example.com
extraction:
  article_content:
    selector: "article"
    fallback: "main"
  title:
    og_meta: "og:title"
    fallback_selector: "h1"
  author:
    json_ld: "author.name"
    fallback_selector: ".author"
  date_published:
    json_ld: "datePublished"
notes: |
  Brief notes about the site structure
```

If CSS selectors won't work, you can define content_pattern:
```yaml
content_pattern:
  start_marker: "<div class=\\"content\\">"
  end_marker: "(?=<footer)"
```

RESPOND ONLY WITH THE YAML CONFIG, NO OTHER TEXT."""

        user_prompt = f"""Analyze this HTML from {domain} and provide extraction rules.

HTML (first 15000 chars):
```html
{html_sample}
```

Provide the YAML configuration:"""

        try:
            response = self.gemini_model.generate_content([
                system_prompt,
                user_prompt
            ])
            
            response_text = response.text.strip()
            
            # Extract YAML from response
            yaml_match = re.search(r'```yaml\n(.*?)\n```', response_text, re.DOTALL)
            if yaml_match:
                yaml_text = yaml_match.group(1)
            else:
                # Try without code fences
                yaml_text = response_text
            
            # Parse YAML
            config = yaml.safe_load(yaml_text)
            
            print(f"   ✓ Received extraction config from AI")
            return config
            
        except Exception as e:
            print(f"   ❌ Error getting config from Gemini: {e}")
            return None
    
    def _ask_gemini_for_better_config(self, html_content, domain, old_config, issue):
        """Ask Gemini to improve the config based on issue"""
        html_sample = html_content[:15000]
        
        system_prompt = """You are fixing extraction rules that didn't work correctly.

Analyze the HTML and the previous config, then provide IMPROVED extraction rules.

Return ONLY the corrected YAML config, no other text."""

        user_prompt = f"""Previous config for {domain} had this issue: {issue}

Previous config:
```yaml
{yaml.dump(old_config, default_flow_style=False)}
```

HTML:
```html
{html_sample}
```

Provide IMPROVED YAML configuration:"""

        try:
            response = self.gemini_model.generate_content([
                system_prompt,
                user_prompt
            ])
            
            response_text = response.text.strip()
            
            # Extract YAML
            yaml_match = re.search(r'```yaml\n(.*?)\n```', response_text, re.DOTALL)
            if yaml_match:
                yaml_text = yaml_match.group(1)
            else:
                yaml_text = response_text
            
            config = yaml.safe_load(yaml_text)
            return config
            
        except Exception as e:
            print(f"   ❌ Error getting improved config: {e}")
            return old_config  # Return old config as fallback
    
    def _validate_extraction(self, original_html, extracted_content):
        """
        Validate extraction quality with Gemini.
        Returns (is_valid, feedback)
        """
        if not self.use_gemini:
            return True, None  # Skip validation if no Gemini
        
        # Truncate for cost
        html_sample = original_html[:10000]
        content_sample = extracted_content[:10000]
        
        system_prompt = """You are validating article extraction quality.

Analyze:
1. Does the extracted content include the FULL article text?
2. Does it EXCLUDE navigation, sidebars, ads, comments, footers?
3. Is the extraction clean and appropriate?

Respond in this EXACT format:
- If good: Just say "APPROVE"
- If issues: List specific problems, one per line"""

        user_prompt = f"""ORIGINAL HTML (first 10000 chars):
```html
{html_sample}
```

EXTRACTED CONTENT (first 10000 chars):
```html
{content_sample}
```

Validate this extraction:"""

        try:
            response = self.gemini_model.generate_content([
                system_prompt,
                user_prompt
            ])
            
            result = response.text.strip()
            
            if result.upper().startswith("APPROVE"):
                return True, None
            else:
                return False, result
                
        except Exception as e:
            print(f"   ❌ Validation error: {e}")
            return True, None  # Assume OK if validation fails


# Example usage
if __name__ == "__main__":
    registry = SiteRegistry()
    
    # Test with ForEntrepreneurs.com
    test_url = "https://www.forentrepreneurs.com/saas-metrics-2/"
    domain = registry.get_domain_from_url(test_url)
    
    config = registry.load_config(domain)
    if config:
        print(f"✓ Loaded config for {domain}")
        print(yaml.dump(config, default_flow_style=False))
    else:
        print(f"No config found for {domain}")

