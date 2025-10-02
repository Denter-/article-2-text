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

# Optional Playwright support
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
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
                    print("✓ Gemini learning enabled (Flash model)")
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
                # NEW: Remove excluded elements before returning
                element = self._apply_exclusions(element, article_config)
                content = str(element)
                # NEW: Apply cleanup rules
                content = self._apply_cleanup_rules(content, article_config)
                return content
        
        # Try fallback selector
        fallback = article_config.get('fallback')
        if fallback:
            element = soup.select_one(fallback)
            if element:
                element = self._apply_exclusions(element, article_config)
                content = str(element)
                content = self._apply_cleanup_rules(content, article_config)
                return content
        
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
    
    def _apply_exclusions(self, element, article_config):
        """Remove excluded elements from the content"""
        exclude_selectors = article_config.get('exclude_selectors', [])
        
        if not exclude_selectors:
            return element
        
        # Make a copy to avoid modifying original
        element_copy = BeautifulSoup(str(element), 'html.parser')
        
        for exclude_selector in exclude_selectors:
            try:
                # Remove all matching elements
                for excluded in element_copy.select(exclude_selector):
                    excluded.decompose()
            except Exception as e:
                # Skip invalid selectors (LLM sometimes generates bad syntax)
                print(f"   ⚠️  Skipping invalid selector '{exclude_selector}': {str(e)[:50]}")
                continue
        
        return element_copy
    
    def _apply_cleanup_rules(self, content, article_config):
        """Apply post-processing cleanup to remove related articles patterns"""
        cleanup = article_config.get('cleanup_rules', {})
        
        if not cleanup:
            return content
        
        # Remove specific patterns
        remove_patterns = cleanup.get('remove_patterns', [])
        for pattern in remove_patterns:
            content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
        
        # Stop at repeated links (common in "related articles" sections)
        if cleanup.get('stop_at_repeated_links', False):
            max_links = cleanup.get('max_consecutive_links', 3)
            content = self._truncate_at_repeated_links(content, max_links)
        
        return content
    
    def _truncate_at_repeated_links(self, content, max_consecutive=3):
        """Truncate content when encountering multiple article links in sequence"""
        # Find patterns like [Read more](/url) or <a href="">Read more</a>
        link_pattern = r'(?:\[.*?Read\s+more.*?\]\([^\)]+\)|<a[^>]*>.*?Read\s+more.*?</a>)'
        
        matches = list(re.finditer(link_pattern, content, re.IGNORECASE | re.DOTALL))
        
        if len(matches) < max_consecutive:
            return content
        
        # Check for clusters of links
        for i in range(len(matches) - max_consecutive + 1):
            cluster = matches[i:i + max_consecutive]
            # If links are close together (within 500 chars), likely related articles
            if cluster[-1].start() - cluster[0].start() < 500:
                # Truncate at the start of this cluster
                return content[:cluster[0].start()]
        
        return content
    
    def check_if_dynamic_content(self, html_content, url):
        """
        Ask LLM if the HTML looks like it requires JavaScript rendering.
        Returns (is_dynamic, reason)
        """
        if not self.use_gemini or not self.gemini_model:
            return False, "LLM not available"
        
        # Sample the HTML (first 5000 chars is usually enough)
        html_sample = html_content[:5000]
        
        prompt = f"""Analyze this HTML and determine if it appears to contain a full article, or if it requires JavaScript to render the content.

HTML Sample:
```html
{html_sample}
```

Look for these indicators of dynamic/incomplete content:
1. Empty article tags or main content areas
2. JSON data in <script> tags that contains article text
3. Minimal visible text content in the body
4. Framework indicators (React, Vue, Angular) with empty containers
5. "Loading..." or placeholder text
6. Paywall indicators

Respond in JSON format:
{{
    "requires_browser": true/false,
    "confidence": "high"/"medium"/"low",
    "reason": "Brief explanation"
}}

Only JSON, no other text."""

        try:
            response = self.gemini_model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Try to extract JSON
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                requires_browser = result.get('requires_browser', False)
                reason = result.get('reason', 'Unknown')
                confidence = result.get('confidence', 'unknown')
                
                if requires_browser:
                    print(f"   🌐 Detected dynamic content (confidence: {confidence})")
                    print(f"      Reason: {reason}")
                
                return requires_browser, reason
            
            return False, "Could not parse LLM response"
            
        except Exception as e:
            print(f"   ⚠️  Dynamic content check failed: {e}")
            return False, str(e)
    
    @staticmethod
    def fetch_with_browser(url, timeout=30000):
        """
        Fetch HTML using Playwright headless browser.
        Returns (success, html_content, error_message)
        """
        if not PLAYWRIGHT_AVAILABLE:
            return False, None, "Playwright not installed. Install with: pip install playwright && playwright install"
        
        try:
            print(f"   🌐 Launching headless browser...")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                print(f"   📄 Loading page with JavaScript...")
                page.goto(url, timeout=timeout, wait_until='networkidle')
                
                # Wait a bit more for any async content
                page.wait_for_timeout(2000)
                
                html_content = page.content()
                browser.close()
                
                print(f"   ✅ Fetched {len(html_content)} bytes (browser-rendered)")
                return True, html_content, None
                
        except Exception as e:
            return False, None, f"Browser fetch failed: {str(e)}"
    
    def learn_from_html(self, url, html_content, force=False, requires_browser=False):
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
        max_iterations = 6
        for iteration in range(max_iterations):
            print(f"\n   Iteration {iteration + 1}/{max_iterations}")
            
            # First iteration: learn extraction rules
            if iteration == 0:
                config = self._ask_gemini_for_config(html_content, domain)
                if not config:
                    return False, None, "Failed to get config from Gemini"
                
                # Add requires_browser flag if detected
                if requires_browser:
                    config['requires_browser'] = True
            
            # Extract content using learned rules (HTML, not converted to MD yet)
            extracted_html = self.extract_with_config(html_content, config)
            
            if not extracted_html:
                print("   ❌ Extraction returned nothing (selector too strict)")
                # On next iteration, validation will detect this and suggest removing filters
                continue
            
            # NEW: Validate by comparing original vs extracted HTML
            print("   🔍 Comparing original vs extracted HTML...")
            is_valid, feedback, filter_changes = self._validate_and_suggest_filters(
                html_content, extracted_html, config
            )
            
            if is_valid:
                print("   ✅ Extraction validated successfully!")
                # Add requires_browser flag before saving
                if requires_browser:
                    config['requires_browser'] = True
                self.save_config(domain, config)
                return True, config, None
            else:
                print(f"   ⚠️  Issue: {feedback}")
                
                if iteration < max_iterations - 1:
                    # Apply filter adjustments iteratively
                    if filter_changes:
                        filters_to_add = filter_changes.get('add', [])
                        filters_to_remove = filter_changes.get('remove', [])
                        
                        if filters_to_add or filters_to_remove:
                            print(f"   🔄 Adjusting filters...")
                            if filters_to_add:
                                print(f"      ➕ Adding {len(filters_to_add)} exclusions")
                            if filters_to_remove:
                                print(f"      ➖ Removing {len(filters_to_remove)} exclusions")
                            
                            # Apply adjustments to config
                            article_config = config.get('extraction', {}).get('article_content', {})
                            current_excludes = article_config.get('exclude_selectors', [])
                            
                            print(f"\n   📋 BEFORE ADJUSTMENT:")
                            print(f"   Current excludes count: {len(current_excludes)}")
                            if current_excludes:
                                print(f"   Sample: {current_excludes[:5]}")
                            
                            # Remove filters
                            for selector in filters_to_remove:
                                if selector in current_excludes:
                                    current_excludes.remove(selector)
                                    print(f"      🗑️  Removed: {selector}")
                            
                            # Add new filters (avoid duplicates)
                            for selector in filters_to_add:
                                if selector not in current_excludes:
                                    current_excludes.append(selector)
                                    print(f"      ✅ Added: {selector}")
                                else:
                                    print(f"      ⏭️  Skipped (duplicate): {selector}")
                            
                            article_config['exclude_selectors'] = current_excludes
                            
                            print(f"\n   📋 AFTER ADJUSTMENT:")
                            print(f"   New excludes count: {len(current_excludes)}")
                            if current_excludes:
                                print(f"   Last 5: {current_excludes[-5:]}")
                            
                            # Keep the same selector, just update exclusions
                            if 'extraction' not in config:
                                config['extraction'] = {}
                            if 'article_content' not in config['extraction']:
                                config['extraction']['article_content'] = {}
                            config['extraction']['article_content'] = article_config
                        else:
                            print("   ⚠️  No filter changes suggested, but extraction has issues")
                    else:
                        print("   ⚠️  Validation did not return filter suggestions")
        
        # Failed after max iterations
        return False, None, f"Failed to learn valid rules after {max_iterations} attempts"
    
    def _ask_gemini_for_config(self, html_content, domain):
        """Ask Gemini to suggest extraction rules"""
        # Truncate HTML for cost efficiency (keep first 15000 chars - should include full article)
        html_sample = html_content[:15000]
        
        system_prompt = """You are an expert at analyzing website HTML structure and creating extraction rules.

Your task: Analyze the HTML and provide CSS selectors or patterns to extract the MAIN ARTICLE CONTENT.

CRITICAL REQUIREMENTS:
1. Extract ONLY the article text content, not navigation, sidebars, ads, comments
2. EXCLUDE "related articles", "recommended reading", "you might also like" sections
3. Watch for these common patterns that indicate NON-CONTENT:
   - Webflow dynamic lists: w-dyn-list, w-dyn-items, collection-list
   - Article cards with thumbnails + "Read more" links
   - Repeated link patterns at the end
   - Navigation to other articles
   - Social sharing buttons (Twitter, Facebook, LinkedIn icons/buttons)
   - "Recommended For You" / "Readers Also Viewed" sections
   - Site navigation menus (header, footer)
   - Author bio sections that appear at the END (after main article)
   - Advertisement containers ("Partner Center", ad slots)
   - Newsletter signup forms, CTAs at the end

EXTRACTION STRATEGY:
- Provide CSS selectors that BeautifulSoup can use
- Use `exclude_selectors` to AGGRESSIVELY remove unwanted sections
- Be VERY liberal with exclusions - it's better to exclude too much than to include UI chrome
- Common patterns to exclude:
  * nav, header, footer elements
  * [class*="share"], [class*="social"]
  * [class*="recommended"], [class*="related"]
  * [class*="ad"], [class*="promo"]
  * [aria-label*="Share"], [aria-label*="Post"]
- Include `cleanup_rules` to stop before related articles
- Include fallback options
- Be specific enough to avoid extracting non-content

Return your answer as valid YAML in this EXACT format:

```yaml
domain: example.com
extraction:
  article_content:
    selector: "article .main-content"
    fallback: "article"
    exclude_selectors:  # IMPORTANT: List selectors to REMOVE from content
      - "nav"
      - "header"
      - "footer"
      - ".w-dyn-list"
      - ".related-articles"
      - ".blog-recommendations"
      - "[class*='collection-list']"
      - "[class*='share']"
      - "[class*='social']"
      - "[class*='recommended']"
      - "[class*='related']"
      - "[class*='promo']"
      - "[class*='ad']"
      - "[aria-label*='Share']"
      - "[aria-label*='Post']"
      - "[role='complementary']"
    cleanup_rules:  # Optional: Post-processing cleanup
      stop_at_repeated_links: true
      max_consecutive_links: 3
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
            # Use Flash model for initial config (fast first attempt)
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
        """Ask Gemini Pro to improve the config based on issue"""
        html_sample = html_content[:15000]
        
        system_prompt = """You are an expert at fixing extraction rules.

Analyze the HTML and the previous config, then provide IMPROVED extraction rules with AGGRESSIVE exclusions.

CRITICAL PATTERNS TO EXCLUDE (real examples from major sites):

1. **Navigation & UI Chrome:**
   - nav, header, footer
   - [class*='Header'], [class*='Menu'], [class*='Nav']
   - Site logo, search bars, login buttons

2. **Social Sharing (major noise source):**
   - [class*='share'], [class*='social']
   - [aria-label*='Share'], [aria-label*='Post'], [aria-label*='Save']
   - [data-analytics*='share'], [data-analytics*='social']
   - button elements with social aria-labels

3. **Recommendations & Related Articles (end-of-article pollution):**
   - [class*='recommended'], [class*='Recommended']
   - [class*='related'], [class*='Related']  
   - [class*='Partner'], [class*='promo']
   - Links to other articles: a[href*='ab=at_art']
   - Product promotions: a[href*='/product/']

4. **Advertisements:**
   - [class*='ad'], [class*='Advertisement']
   - iframe[title*='Advertisement']
   - [role='complementary']

5. **Utility Elements:**
   - Print/Save/Buy buttons
   - Newsletter signups
   - CTAs at the end
   - Author bios AFTER article conclusion

STRATEGY:
- Be VERY aggressive with exclusions - better to exclude too much than include UI
- Use CSS attribute selectors with wildcards INSIDE brackets: [class*='pattern']
  CORRECT: [class*='Header'], [class*='Menu'], [aria-label*='Share']
  WRONG: .Header-*, button-*  (wildcards don't work as suffixes in CSS)
- Use exact class names for specific patterns: .Header-module_header__qxHtx
- Target both specific classes AND generic patterns
- Look for patterns in the HTML that repeat across multiple unwanted sections

If extraction is incomplete:
- Try more specific selector for main content container
- Check if content is in nested divs or semantic tags
- Consider content_pattern approach

Return ONLY the corrected YAML config, no other text."""

        user_prompt = f"""Previous config for {domain} had this issue: {issue}

Previous config that FAILED:
```yaml
{yaml.dump(old_config, default_flow_style=False)}
```

HTML (analyze carefully - look for patterns in class names):
```html
{html_sample}
```

Provide IMPROVED YAML configuration with MORE AGGRESSIVE exclude_selectors:"""

        try:
            # Use Flash model
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
    
    def _validate_and_suggest_filters(self, original_html, extracted_html, current_config):
        """
        Validate extraction by comparing original vs cleaned HTML.
        Returns (is_valid, feedback, suggested_filter_changes)
        
        The LLM sees both versions and suggests filter adjustments.
        """
        if not self.use_gemini:
            return True, None, None  # Skip validation if no Gemini
        
        # Sample start, middle, and END (to catch "Recommended" sections)
        html_len = len(original_html)
        content_len = len(extracted_html)
        
        # Show beginning and end of both versions for comparison
        original_sample = original_html[:8000] + "\n\n[...MIDDLE...]\n\n" + original_html[max(0, html_len-3000):]
        extracted_sample = extracted_html[:8000] + "\n\n[...MIDDLE...]\n\n" + extracted_html[max(0, content_len-3000):]
        
        # Get current exclude_selectors
        current_excludes = current_config.get('extraction', {}).get('article_content', {}).get('exclude_selectors', [])
        
        system_prompt = """You are comparing ORIGINAL HTML vs EXTRACTED HTML to validate article extraction.

Your task: Compare the two versions and determine if the extraction is correct.

GOOD EXTRACTION should:
1. Include FULL article text from start to finish
2. EXCLUDE all UI chrome: navigation, social buttons, ads, "Recommended" sections, related articles

Compare the START, MIDDLE, and END of both versions:

PROBLEMS TO DETECT:
- **Too much noise** (extracted includes UI elements that should be removed)
- **Too aggressive** (extracted removed actual article content)

Respond in JSON format:
```json
{
  "status": "approve" or "needs_filters" or "too_aggressive",
  "issue_description": "Brief description of what's wrong",
  "filters_to_add": [
    "CSS selector 1",
    "CSS selector 2"
  ],
  "filters_to_remove": [
    "CSS selector that was too aggressive"
  ]
}
```

**If status is "approve"**: Leave filters arrays empty
**If "needs_filters"**: Provide CSS selectors to ADD to exclude_selectors
**If "too_aggressive"**: Provide CSS selectors to REMOVE from exclude_selectors

CSS SELECTOR SYNTAX (IMPORTANT):
- Attribute wildcards: [class*='Header'], [aria-label*='Share']  
- Exact classes: .specific-class-name
- Generic tags: nav, header, footer, button
- Combined: button[aria-label*='Save']

Only JSON, no other text."""

        user_prompt = f"""Compare these two versions:

ORIGINAL HTML (full page with UI):
```html
{original_sample}
```

EXTRACTED HTML (after applying filters):
```html
{extracted_sample}
```

Current exclude_selectors being used:
```yaml
{yaml.dump(current_excludes, default_flow_style=False)}
```

Analyze and provide filter adjustments:"""

        try:
            # Use Flash model for validation (fast and cost-effective)
            model = self.gemini_model
            
            # Log the prompt being sent
            print(f"\n   📤 SENDING TO LLM:")
            print(f"   System prompt length: {len(system_prompt)} chars")
            print(f"   User prompt length: {len(user_prompt)} chars")
            print(f"   Original HTML sample length: {len(original_sample)} chars")
            print(f"   Extracted HTML sample length: {len(extracted_sample)} chars")
            
            response = model.generate_content([
                system_prompt,
                user_prompt
            ])
            
            result = response.text.strip()
            
            # Log the raw response
            print(f"\n   📥 LLM RESPONSE:")
            print(f"   Response length: {len(result)} chars")
            print(f"   First 500 chars: {result[:500]}")
            if len(result) > 500:
                print(f"   Last 300 chars: {result[-300:]}")
            
            # Try to extract JSON with filter suggestions
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                print(f"\n   🔍 PARSED JSON:")
                print(f"   {json_str[:800]}")
                
                validation_result = json.loads(json_str)
                status = validation_result.get('status', '').lower()
                
                print(f"\n   ✨ EXTRACTED FILTERS:")
                print(f"   Status: {status}")
                
                if status == 'approve':
                    print(f"   ✅ Approved - no changes needed")
                    return True, None, None
                else:
                    issue = validation_result.get('issue_description', 'Unknown issue')
                    filters_to_add = validation_result.get('filters_to_add', [])
                    filters_to_remove = validation_result.get('filters_to_remove', [])
                    
                    print(f"   Issue: {issue}")
                    print(f"   Filters to add ({len(filters_to_add)}): {filters_to_add}")
                    print(f"   Filters to remove ({len(filters_to_remove)}): {filters_to_remove}")
                    
                    return False, issue, {
                        'add': filters_to_add,
                        'remove': filters_to_remove
                    }
            else:
                # Fallback to old format
                if "APPROVE" in result.upper():
                    return True, None, None
                else:
                    return False, result, None
                
        except Exception as e:
            print(f"   ❌ Validation error: {e}")
            return True, None, None  # Assume OK if validation fails


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

