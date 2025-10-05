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
try:
    from .extraction_engine import ExtractionEngine
except ImportError:
    from extraction_engine import ExtractionEngine

# Optional Gemini support
GEMINI_AVAILABLE = False
try:
    from google import genai
    from google.genai.types import GenerateContentConfig, ThinkingConfig
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
        self.gemini_client = None
        self.request_timeout_s = 60  # LLM call target timeout
        self.extraction_engine = ExtractionEngine()
        
        if self.use_gemini:
            api_key = os.getenv('GEMINI_API_KEY')
            if api_key:
                try:
                    self.gemini_client = genai.Client(api_key=api_key)
                    print("✓ Gemini learning enabled (2.5 Flash - thinking disabled)")
                except Exception as e:
                    print(f"⚠️  Gemini init failed: {e}")
                    self.use_gemini = False

    def _generate_with_retry(self, contents, max_retries=2):
        """Call Gemini with basic retry and extended timeout budget."""
        if not self.gemini_client:
            raise RuntimeError("Gemini client is not initialized")
        last_err = None
        for attempt in range(max_retries):
            try:
                # Configure with thinking disabled for faster responses
                config = GenerateContentConfig(
                    temperature=0.1,
                    top_p=0.95,
                    top_k=40,
                    max_output_tokens=8192,
                    thinking_config=ThinkingConfig(thinking_budget=0)
                )
                response = self.gemini_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=contents,
                    config=config
                )
                return response
            except Exception as e:
                last_err = e
                print(f"   ❌ LLM call failed (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    import time
                    backoff = min(5 * (attempt + 1), 10)
                    print(f"   ⏳ Retrying after {backoff}s...")
                    time.sleep(backoff)
        raise last_err
    
    def get_domain_from_url(self, url):
        """Extract domain from URL"""
        parsed = urlparse(url)
        domain = parsed.netloc
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    
    def clean_html_for_learning(self, html_content):
        """Clean HTML by removing irrelevant fragments before learning/extraction"""
        if not html_content:
            return html_content
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Only remove script and style elements (keep everything else for now)
        for element in soup(['script', 'style', 'noscript']):
            element.decompose()
        
        # Remove only the most obvious irrelevant elements
        obvious_irrelevant = [
            'script', 'style', 'noscript',
            'iframe', 'embed', 'object'
        ]
        
        for selector in obvious_irrelevant:
            try:
                for element in soup.select(selector):
                    element.decompose()
            except Exception:
                continue
        
        return str(soup)
    
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
        return self.extraction_engine.extract_article_html(html_content, config)
    
    
    def check_if_dynamic_content(self, html_content, url):
        """
        Ask LLM if the HTML looks like it requires JavaScript rendering.
        Returns (is_dynamic, reason)
        """
        if not self.use_gemini or not self.gemini_client:
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
            response = self._generate_with_retry(prompt)
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
        Learn extraction rules using inverted approach: extract everything, identify noise, exclude it.
        Returns (success, config, error_message)
        """
        if not self.use_gemini:
            return False, None, "Gemini not available for learning"
        
        # Use inverted learning approach
        try:
            from .inverted_learning import InvertedLearner
        except ImportError:
            from inverted_learning import InvertedLearner
        learner = InvertedLearner(use_gemini=True)
        learner.gemini_client = self.gemini_client  # Reuse our initialized client
        
        success, config, error = learner.learn_from_html(url, html_content)
        
        if success and config:
            # Save the config
            domain = self.get_domain_from_url(url)
            if requires_browser:
                config['requires_browser'] = True
            self.save_config(domain, config)
        
        return success, config, error
    
    def learn_from_html_old(self, url, html_content, force=False, requires_browser=False):
        """
        Learn extraction rules from HTML using Gemini.
        Returns (success, config, error_message)
        """
        domain = self.get_domain_from_url(url)
        
        print(f"\n{'='*80}")
        print(f"🧠 LEARNING EXTRACTION RULES FOR {domain.upper()}")
        print(f"{'='*80}")
        print(f"URL: {url}")
        print(f"HTML Content Length: {len(html_content):,} characters")
        print(f"Force Mode: {force}")
        print(f"Requires Browser: {requires_browser}")
        
        # Check if config exists
        if not force:
            existing_config = self.load_config(domain)
            if existing_config:
                print(f"✓ Config exists for {domain} (use --force-renew to recreate)")
                return True, existing_config, None
        
        if not self.use_gemini:
            return False, None, "Gemini not available - cannot learn new site"
        
        print(f"\n🔍 ANALYZING HTML STRUCTURE WITH AI...")
        
        # Log HTML structure analysis
        soup = BeautifulSoup(html_content, 'html.parser')
        print(f"\n📊 HTML STRUCTURE ANALYSIS:")
        print(f"   - Total elements: {len(soup.find_all())}")
        print(f"   - Article tags: {len(soup.find_all('article'))}")
        print(f"   - Main tags: {len(soup.find_all('main'))}")
        print(f"   - H1 tags: {len(soup.find_all('h1'))}")
        print(f"   - H2 tags: {len(soup.find_all('h2'))}")
        print(f"   - P tags: {len(soup.find_all('p'))}")
        print(f"   - Div tags: {len(soup.find_all('div'))}")
        
        # Show some key elements
        print(f"\n🔍 KEY ELEMENTS FOUND:")
        if soup.find('article'):
            print(f"   - Article tag found: {soup.find('article').get('class', 'no-class')}")
        if soup.find('main'):
            print(f"   - Main tag found: {soup.find('main').get('class', 'no-class')}")
        if soup.find('h1'):
            print(f"   - H1 found: '{soup.find('h1').get_text()[:100]}...'")
        
        # Ask Gemini to analyze the site
        max_iterations = 6
        feedback = None  # Initialize feedback variable
        
        for iteration in range(max_iterations):
            print(f"\n{'='*60}")
            print(f"🔄 ITERATION {iteration + 1}/{max_iterations}")
            print(f"{'='*60}")
            
            # First iteration: learn extraction rules
            if iteration == 0:
                print(f"\n🤖 ASKING GEMINI FOR INITIAL CONFIG...")
                config = self._ask_gemini_for_config(html_content, domain)
                if not config:
                    print(f"❌ FAILED: No config returned from Gemini")
                    return False, None, "Failed to get config from Gemini"
                
                print(f"\n✅ GEMINI CONFIG RECEIVED:")
                print(f"   Domain: {config.get('domain', 'NOT SET')}")
                print(f"   Article selector: {config.get('extraction', {}).get('article_content', {}).get('selector', 'NOT SET')}")
                print(f"   Fallback selector: {config.get('extraction', {}).get('article_content', {}).get('fallback', 'NOT SET')}")
                print(f"   Exclude selectors: {len(config.get('extraction', {}).get('article_content', {}).get('exclude_selectors', []))}")
                
                # Add requires_browser flag if detected
                if requires_browser:
                    config['requires_browser'] = True
                    print(f"   Requires browser: {requires_browser}")
            else:
                print(f"\n🤖 ASKING GEMINI FOR IMPROVED CONFIG...")
                old_config = config.copy()
                config = self._ask_gemini_for_better_config(html_content, domain, old_config, feedback or "Extraction failed")
                if not config:
                    print(f"❌ FAILED: No improved config returned from Gemini")
                    config = old_config  # Fallback to old config
                else:
                    print(f"\n✅ IMPROVED CONFIG RECEIVED:")
                    print(f"   Article selector: {config.get('extraction', {}).get('article_content', {}).get('selector', 'NOT SET')}")
                    print(f"   Exclude selectors: {len(config.get('extraction', {}).get('article_content', {}).get('exclude_selectors', []))}")
            
            # Extract content using learned rules (HTML, not converted to MD yet)
            print(f"\n🔍 TESTING EXTRACTION WITH CURRENT CONFIG...")
            extracted_html = self.extract_with_config(html_content, config)
            
            if not extracted_html:
                print("❌ EXTRACTION FAILED: No content returned (selector too strict)")
                print(f"   Current selector: {config.get('extraction', {}).get('article_content', {}).get('selector', 'NOT SET')}")
                print(f"   Current fallback: {config.get('extraction', {}).get('article_content', {}).get('fallback', 'NOT SET')}")
                feedback = "No content extracted - selector too strict"
                # On next iteration, validation will detect this and suggest removing filters
                continue
            
            print(f"✅ EXTRACTION SUCCESSFUL:")
            print(f"   Extracted content length: {len(extracted_html):,} characters")
            print(f"   First 200 chars: {extracted_html[:200]}...")
            print(f"   Last 200 chars: ...{extracted_html[-200:]}")
            
            # NEW: Validate by comparing original vs extracted HTML
            print(f"\n🔍 VALIDATING EXTRACTION QUALITY...")
            is_valid, feedback, filter_changes = self._validate_and_suggest_filters(
                html_content, extracted_html, config
            )
            
            if is_valid:
                print("✅ EXTRACTION VALIDATED SUCCESSFULLY!")
                # Add requires_browser flag before saving
                if requires_browser:
                    config['requires_browser'] = True
                self.save_config(domain, config)
                return True, config, None
            else:
                print(f"⚠️  VALIDATION ISSUE: {feedback}")
                
                if iteration < max_iterations - 1:
                    # Apply filter adjustments iteratively
                    if filter_changes:
                        filters_to_add = filter_changes.get('add', [])
                        filters_to_remove = filter_changes.get('remove', [])
                        
                        if filters_to_add or filters_to_remove:
                            print(f"\n🔄 APPLYING FILTER ADJUSTMENTS...")
                            if filters_to_add:
                                print(f"   ➕ Adding {len(filters_to_add)} exclusions: {filters_to_add}")
                            if filters_to_remove:
                                print(f"   ➖ Removing {len(filters_to_remove)} exclusions: {filters_to_remove}")
                            
                            # Apply adjustments to config
                            article_config = config.get('extraction', {}).get('article_content', {})
                            current_excludes = article_config.get('exclude_selectors', [])
                            
                            print(f"\n📋 FILTER ADJUSTMENT DETAILS:")
                            print(f"   Before: {len(current_excludes)} exclude selectors")
                            if current_excludes:
                                print(f"   Current excludes: {current_excludes[:10]}{'...' if len(current_excludes) > 10 else ''}")
                            
                            # Remove filters
                            for selector in filters_to_remove:
                                if selector in current_excludes:
                                    current_excludes.remove(selector)
                                    print(f"   🗑️  Removed: {selector}")
                                else:
                                    print(f"   ⚠️  Not found to remove: {selector}")
                            
                            # Add new filters (avoid duplicates)
                            for selector in filters_to_add:
                                if selector not in current_excludes:
                                    current_excludes.append(selector)
                                    print(f"   ✅ Added: {selector}")
                                else:
                                    print(f"   ⏭️  Skipped (duplicate): {selector}")
                            
                            article_config['exclude_selectors'] = current_excludes
                            
                            print(f"\n📋 AFTER ADJUSTMENT:")
                            print(f"   New count: {len(current_excludes)} exclude selectors")
                            if current_excludes:
                                print(f"   New excludes: {current_excludes[-10:]}{'...' if len(current_excludes) > 10 else ''}")
                            
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
                else:
                    print(f"\n❌ MAX ITERATIONS REACHED - LEARNING FAILED")
        
        # Failed after max iterations
        print(f"\n{'='*80}")
        print(f"❌ LEARNING FAILED AFTER {max_iterations} ATTEMPTS")
        print(f"{'='*80}")
        return False, None, f"Failed to learn valid rules after {max_iterations} attempts"
    
    def _ask_gemini_for_config(self, html_content, domain):
        """Ask Gemini to suggest extraction rules"""
        # Truncate HTML for cost efficiency (keep first 15000 chars - should include full article)
        # Clean HTML first to remove irrelevant fragments
        cleaned_html = self.clean_html_for_learning(html_content)
        print(f"   HTML cleaned: {len(html_content):,} -> {len(cleaned_html):,} characters")
        
        # Take a larger sample of cleaned HTML for analysis (first 200k chars)
        html_sample = cleaned_html[:200000]
        
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

MODERN SITE STRUCTURES TO CONSIDER:
- **Elementor (WordPress)**: Look for `.elementor-widget-theme-post-content` or `.elementor-element` with content
- **Gutenberg (WordPress)**: Look for `.wp-block-post-content` or `.entry-content`
- **Divi (WordPress)**: Look for `.et_pb_post_content` or `.entry-content`
- **Custom themes**: May use `.post-content`, `.entry-content`, or `.content`
- **Headless CMS**: May use semantic HTML5 tags like `<main>`, `<article>`, or custom divs
- **React/Vue/Angular**: Content might be in divs with data attributes or specific class patterns

EXTRACTION STRATEGY:
- FIRST: Look for the actual content container by analyzing the HTML structure
- Check if there are `<article>`, `<main>`, or content-specific divs
- For page builders (Elementor, Divi, etc.), look for their specific content widgets
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

ANALYSIS PROCESS:
1. Look for the H1 tag and trace its container hierarchy
2. Find the div that contains substantial text content (>2000 characters) AND the H1 tag
3. Check for common content indicators: multiple H2s, paragraphs, lists
4. Identify the specific selector for that content container
5. Create aggressive exclusions for non-content elements

CRITICAL: The content container MUST contain the H1 tag. If a div has lots of text but no H1, it's likely not the main article content.

COMMON PATTERNS:
- Elementor: `div.elementor` (the main container)
- WordPress: `div.entry-content` or `article .entry-content`
- Custom: Look for divs with classes like `post-content`, `content`, `main-content`
- Page builders: Look for the main container div, not nested content widgets

Return your answer as valid YAML in this EXACT format:

```yaml
domain: example.com
extraction:
  article_content:
    selector: "div.elementor-widget-theme-post-content"  # Use the actual content container
    fallback: "main"  # Or another fallback
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
  Brief notes about the site structure (e.g., "Elementor-based WordPress site")
```

If CSS selectors won't work, you can define content_pattern:
```yaml
content_pattern:
  start_marker: "<div class=\\"content\\">"
  end_marker: "(?=<footer)"
```

RESPOND ONLY WITH THE YAML CONFIG, NO OTHER TEXT."""

        user_prompt = f"""Analyze this HTML from {domain} and provide extraction rules.

IMPORTANT: Find the div that contains BOTH the H1 tag AND substantial text content (>2000 characters). This is the main article container.

HTML (first 15000 chars):
```html
{html_sample}
```

Steps:
1. Find the H1 tag in the HTML
2. Trace up the DOM hierarchy to find the div that contains the H1
3. Check if that div has substantial text content (multiple paragraphs, headings)
4. Use that div's class as the selector

Provide the YAML configuration:"""

        try:
            print(f"\n📤 SENDING TO GEMINI:")
            print(f"   Domain: {domain}")
            print(f"   HTML sample length: {len(html_sample):,} characters")
            print(f"   System prompt length: {len(system_prompt):,} characters")
            print(f"   User prompt length: {len(user_prompt):,} characters")
            print(f"\n🔍 FULL SYSTEM PROMPT:")
            print("="*80)
            print(system_prompt)
            print("="*80)
            print(f"\n🔍 FULL USER PROMPT:")
            print("="*80)
            print(user_prompt)
            print("="*80)
            
            # Use Flash model with retry wrapper
            response = self._generate_with_retry([
                system_prompt,
                user_prompt
            ])
            
            response_text = response.text.strip()
            print(f"\n📥 GEMINI RESPONSE:")
            print(f"   Response length: {len(response_text):,} characters")
            print(f"\n🔍 FULL GEMINI RESPONSE:")
            print("="*80)
            print(response_text)
            print("="*80)
            
            # Extract YAML from response
            yaml_match = re.search(r'```yaml\n(.*?)\n```', response_text, re.DOTALL)
            if yaml_match:
                yaml_text = yaml_match.group(1)
                print(f"   ✅ Found YAML in code fences")
            else:
                # Try without code fences
                yaml_text = response_text
                print(f"   ⚠️  No code fences found, using full response")
            
            print(f"\n🔍 PARSING YAML:")
            print(f"   YAML text length: {len(yaml_text):,} characters")
            print(f"   YAML preview: {yaml_text[:500]}...")
            
            # Parse YAML
            config = yaml.safe_load(yaml_text)
            
            if config:
                print(f"   ✅ YAML parsed successfully")
                print(f"   Config keys: {list(config.keys())}")
            else:
                print(f"   ❌ YAML parsing returned None")
            
            return config
            
        except Exception as e:
            print(f"   ❌ Error getting config from Gemini: {e}")
            print(f"   Exception type: {type(e).__name__}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
            return None
    
    def _ask_gemini_for_better_config(self, html_content, domain, old_config, issue):
        """Ask Gemini Pro to improve the config based on issue"""
        # Clean HTML first to remove irrelevant fragments
        cleaned_html = self.clean_html_for_learning(html_content)
        print(f"   HTML cleaned: {len(html_content):,} -> {len(cleaned_html):,} characters")
        
        # Take a larger sample of cleaned HTML for analysis (first 200k chars)
        html_sample = cleaned_html[:200000]
        
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

MODERN SITE STRUCTURES TO CONSIDER:
- **Elementor (WordPress)**: Look for `.elementor-widget-theme-post-content` or `.elementor-element` with content
- **Gutenberg (WordPress)**: Look for `.wp-block-post-content` or `.entry-content`
- **Divi (WordPress)**: Look for `.et_pb_post_content` or `.entry-content`
- **Custom themes**: May use `.post-content`, `.entry-content`, or `.content`
- **Headless CMS**: May use semantic HTML5 tags like `<main>`, `<article>`, or custom divs

STRATEGY:
- FIRST: Identify the actual content container by analyzing the HTML structure
- Look for the H1 tag and trace its container hierarchy to find the content div
- For page builders (Elementor, Divi, etc.), look for their specific content widgets
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
- Look for the div that contains substantial text content (>2000 characters)

Return ONLY the corrected YAML config, no other text."""

        # Extract previous selectors/excludes to ground the model
        prev_selector = old_config.get('extraction', {}).get('article_content', {}).get('selector')
        prev_fallback = old_config.get('extraction', {}).get('article_content', {}).get('fallback')
        prev_excludes = old_config.get('extraction', {}).get('article_content', {}).get('exclude_selectors', [])

        user_prompt = f"""Previous config for {domain} had this issue: {issue}

Previous config that FAILED (consider switching strategy if selectors are wrong):
```yaml
selector: {prev_selector}
fallback: {prev_fallback}
exclude_selectors_count: {len(prev_excludes)}
```

HTML (analyze carefully - look for patterns in class names, page builder containers, and H1 container ancestry):
```html
{html_sample}
```

Your task:
1. If the selector approach was wrong (no matches), RE-THINK the container strategy. Prefer the container that CONTAINS the H1 and substantial text.
2. If selectors are unreliable, propose a `content_pattern` with conservative start/end markers.
3. Keep `exclude_selectors` aggressive but syntactically valid (no wildcard suffixes).
4. Return ONLY the corrected YAML config (same schema)."""

        try:
            print(f"\n🔍 FULL IMPROVED CONFIG SYSTEM PROMPT:")
            print("="*80)
            print(system_prompt)
            print("="*80)
            print(f"\n🔍 FULL IMPROVED CONFIG USER PROMPT:")
            print("="*80)
            print(user_prompt)
            print("="*80)
            
            # Use Flash model
            response = self._generate_with_retry([
                system_prompt,
                user_prompt
            ])
            
            response_text = response.text.strip()
            print(f"\n📥 IMPROVED CONFIG GEMINI RESPONSE:")
            print(f"   Response length: {len(response_text):,} characters")
            print(f"\n🔍 FULL IMPROVED CONFIG GEMINI RESPONSE:")
            print("="*80)
            print(response_text)
            print("="*80)
            
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
            # Log the prompt being sent
            print(f"\n   📤 SENDING TO LLM:")
            print(f"   System prompt length: {len(system_prompt)} chars")
            print(f"   User prompt length: {len(user_prompt)} chars")
            print(f"   Original HTML sample length: {len(original_sample)} chars")
            print(f"   Extracted HTML sample length: {len(extracted_sample)} chars")
            
            response = self._generate_with_retry([
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

