#!/usr/bin/env python3
"""
Inverted Learning Approach:
Instead of guessing selectors, we extract everything, identify noise, then find selectors to exclude it.
"""

import re
import yaml
import os
from bs4 import BeautifulSoup
from typing import Dict, List, Tuple, Optional

# Optional Gemini support
GEMINI_AVAILABLE = False
try:
    from google import genai
    from google.genai.types import GenerateContentConfig, ThinkingConfig
    GEMINI_AVAILABLE = True
except ImportError:
    pass


class InvertedLearner:
    """Learn extraction rules by identifying noise to exclude, not content to include"""
    
    def __init__(self, use_gemini=True):
        self.use_gemini = use_gemini and GEMINI_AVAILABLE
        self.gemini_client = None
        
        if self.use_gemini:
            api_key = os.getenv('GEMINI_API_KEY')
            if api_key:
                try:
                    self.gemini_client = genai.Client(api_key=api_key)
                    print("✓ Gemini inverted learning enabled (2.5 Flash - thinking disabled)")
                except Exception as e:
                    print(f"⚠️  Gemini init failed: {e}")
                    self.use_gemini = False
    
    def _generate_content(self, contents):
        """Helper to call Gemini with thinking disabled"""
        if not self.gemini_client:
            raise RuntimeError("Gemini client is not initialized")
        
        config = GenerateContentConfig(
            temperature=0.1,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
            thinking_config=ThinkingConfig(thinking_budget=0)
        )
        
        return self.gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=config
        )
    
    def find_article_boundaries(self, extracted_text: str, html_content: str) -> Dict:
        """
        Ask LLM to identify CSS selectors that mark the START and END of the article content.
        This helps us extract just the article block, then apply exclusions within it.
        """
        if not self.gemini_client:
            return {}
        
        # Prepare samples: beginning and end (where boundaries are)
        if len(extracted_text) > 10000:
            text_sample = extracted_text[:5000] + "\n\n[... middle content ...]\n\n" + extracted_text[-5000:]
        else:
            text_sample = extracted_text
        
        # HTML: show beginning and end structure
        if len(html_content) > 80000:
            html_sample = html_content[:40000] + "\n\n<!-- ... middle ... -->\n\n" + html_content[-40000:]
        else:
            html_sample = html_content
        
        system_prompt = """You are an expert at identifying article boundaries in HTML.

Your task:
1. Find the FIRST element of the article (where article begins)
2. Find the FIRST element AFTER the article (where article ends)

HOW IT WORKS:
- Start selector: We delete everything BEFORE this element (keep the element itself)
- End selector: We delete this element and everything AFTER it
- Example: If start=".article-title" and end=".related-articles", we keep everything from .article-title up to (but not including) .related-articles

CRITICAL RULES FOR SELECTORS:
1. Copy class and id names EXACTLY as they appear in HTML - character by character
2. Preserve ALL special characters: underscores (_), hyphens (-), numbers, etc.
3. DO NOT change or "normalize" class names - use them VERBATIM from the HTML
4. Example: If HTML has class="section_blog-post_header" use EXACTLY ".section_blog-post_header"
5. DO NOT invent or modify class names - only use what you SEE in the HTML

WHAT TO LOOK FOR:
- Start selector: The FIRST article element (title, header, or first paragraph)
  * Could be: h1, .article-title, .post-header, .blog-post_header, etc.
  * Should come AFTER navigation/menus
- End selector: The FIRST non-article element (related articles, comments, footer)
  * Could be: .related-articles, .comments-section, footer, .newsletter-signup
  * Should come AFTER the last article paragraph

IMPORTANT:
- Start can be just the title/header - we'll keep everything from there onwards
- End marks where noise begins - we'll delete from there onwards
- If no clear boundaries exist, return empty

Return ONLY valid YAML in this format:

```yaml
has_boundaries: true  # or false if no clear boundaries found
article_start:
  selector: "article.post-content"  # EXACT CSS selector from HTML
  reasoning: "Contains h1 title and all paragraphs"
article_end:  # Optional: elements that mark end of article
  selector: ".related-articles-section"  # EXACT CSS selector from HTML
  reasoning: "Section with related articles that appears after main content"
```

If no clear boundaries, return:
```yaml
has_boundaries: false
reasoning: "Content mixed with navigation, no clear container"
```"""

        user_prompt = f"""Analyze this HTML to find article boundary selectors.

EXTRACTED TEXT (to understand what is article vs noise):
```
{text_sample}
```

HTML STRUCTURE (find the boundary elements):
```html
{html_sample}
```

Find:
1. Start selector: The FIRST element of the article (title, header, or first content element)
   - We'll delete everything BEFORE this, but keep this element and everything after
2. End selector: The FIRST element AFTER the article ends (related articles, comments, footer)
   - We'll delete this element and everything after it

EXAMPLES:
✅ GOOD: start=".section_blog-post_header" end=".section_blog-post_related-articles"
✅ GOOD: start="h1.article-title" end=".comments-section"  
✅ GOOD: start="article" end="footer"

Return ONLY the YAML with EXACT class names from HTML, no other text."""

        try:
            print(f"\n🤖 ASKING GEMINI TO IDENTIFY ARTICLE BOUNDARIES...")
            print(f"   Text sample: {len(text_sample):,} chars")
            print(f"   HTML sample: {len(html_sample):,} chars")
            
            # Retry logic
            max_retries = 3
            last_error = None
            for attempt in range(max_retries):
                try:
                    print(f"   Attempt {attempt + 1}/{max_retries}...")
                    response = self._generate_content([system_prompt, user_prompt])
                    break
                except Exception as e:
                    last_error = e
                    error_msg = str(e)
                    if "504" in error_msg or "timeout" in error_msg.lower() or "DeadlineExceeded" in error_msg:
                        if attempt < max_retries - 1:
                            import time
                            wait_time = 10 * (attempt + 1)
                            print(f"   ⏳ Timeout, retrying in {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                    raise
            else:
                # All retries failed
                print(f"❌ All {max_retries} attempts failed: {last_error}")
                return {}
            
            response_text = response.text.strip()
            
            print(f"\n📥 LLM RESPONSE (boundaries):")
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
            
            if config.get('has_boundaries'):
                start = config.get('article_start', {})
                end = config.get('article_end', {})
                print(f"   ✅ Found boundaries:")
                print(f"      Start: {start.get('selector', 'N/A')}")
                print(f"      End: {end.get('selector', 'N/A')}")
            else:
                print(f"   ℹ️  No clear boundaries found: {config.get('reasoning', 'N/A')}")
            
            return config
            
        except Exception as e:
            print(f"❌ Error finding boundaries: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def refine_boundaries(self, extracted_text: str, html_content: str, current_start: str, current_end: Optional[str], validation_feedback: Dict) -> Dict:
        """
        Refine boundary selectors based on validation feedback.
        If validation says there's noise at beginning/end, find tighter boundaries.
        """
        if not self.gemini_client:
            return {'has_boundaries': False}
        
        # Prepare samples
        if len(extracted_text) > 10000:
            text_sample = extracted_text[:5000] + "\n\n[... middle ...]\n\n" + extracted_text[-5000:]
        else:
            text_sample = extracted_text
        
        if len(html_content) > 80000:
            html_sample = html_content[:40000] + "\n\n<!-- ... middle ... -->\n\n" + html_content[-40000:]
        else:
            html_sample = html_content
        
        # Get feedback about what needs fixing
        under_removed = validation_feedback.get('under_removed', [])
        
        system_prompt = """You are an expert at refining article boundary selectors.

The current boundaries are NOT tight enough - there's still noise at the beginning or end.

Your task:
1. Look at the CURRENT selectors that were tried
2. Look at the NOISE that still remains (text samples provided)
3. Find TIGHTER/BETTER selectors that exclude this noise

CRITICAL RULES FOR SELECTORS:
1. Copy class and id names EXACTLY as they appear in HTML - character by character
2. Preserve ALL special characters: underscores (_), hyphens (-), numbers, etc.
3. DO NOT change or "normalize" class names - use them VERBATIM from the HTML
4. Example: If HTML has class="section_blog-post_header" use EXACTLY ".section_blog-post_header"

STRATEGY:
- If noise is at BEGINNING: Find a selector that starts AFTER the noise
- If noise is at END: Find a selector that marks where the noise BEGINS (article ends there)
- Be MORE SPECIFIC than the current selectors

Return ONLY valid YAML:

```yaml
has_boundaries: true
article_start:
  selector: ".tighter-selector"  # EXACT selector that excludes beginning noise
  reasoning: "Skips navigation, starts at article title"
article_end:  # Optional
  selector: ".noise-starts-here"  # EXACT selector where noise begins
  reasoning: "Marks start of related articles section"
```"""

        current_end_text = f" Current end: {current_end}" if current_end else " No end boundary"
        noise_samples = "\n".join([f"- \"{item.get('text_sample', '')[:100]}...\"" for item in under_removed[:5]])
        
        user_prompt = f"""Current boundaries are not tight enough. Refine them.

CURRENT BOUNDARIES:
- Start: {current_start}
-{current_end_text}

NOISE STILL PRESENT (should NOT be in article):
{noise_samples}

EXTRACTED TEXT (with noise):
```
{text_sample}
```

HTML STRUCTURE:
```html
{html_sample}
```

Find TIGHTER boundaries that exclude the noise shown above.
Return ONLY the YAML, no other text."""

        try:
            print(f"\n🔧 REFINING ARTICLE BOUNDARIES...")
            print(f"   Current start: {current_start}")
            print(f"   Current end: {current_end or 'None'}")
            print(f"   Noise issues: {len(under_removed)}")
            
            # Retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    print(f"   Attempt {attempt + 1}/{max_retries}...")
                    response = self._generate_content([system_prompt, user_prompt])
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(10 * (attempt + 1))
                        continue
                    raise
            
            response_text = response.text.strip()
            
            print(f"\n📥 LLM RESPONSE (refined boundaries):")
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
            
            if config.get('has_boundaries'):
                start = config.get('article_start', {})
                end = config.get('article_end', {})
                print(f"   ✅ Refined boundaries:")
                print(f"      Start: {start.get('selector', 'N/A')}")
                print(f"      End: {end.get('selector', 'N/A')}")
            
            return config
            
        except Exception as e:
            print(f"❌ Error refining boundaries: {e}")
            import traceback
            traceback.print_exc()
            return {'has_boundaries': False}
    
    def extract_with_boundaries(self, html_content: str, start_selector: Optional[str], end_selector: Optional[str]) -> str:
        """
        Extract HTML using boundary selectors.
        - Start selector: Delete everything BEFORE this element (keep the element itself)
        - End selector: Delete this element and everything AFTER it
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # If we have a start boundary, delete everything before it
        if start_selector:
            try:
                start_element = soup.select_one(start_selector)
                if start_element:
                    # Delete all previous siblings recursively up the tree
                    current = start_element
                    while current:
                        # Delete all previous siblings at this level
                        for sibling in list(current.find_previous_siblings()):
                            sibling.decompose()
                        # Move up to parent
                        current = current.parent
                        # Stop if we reach body or html
                        if current and current.name in ['body', 'html', '[document]']:
                            break
                    print(f"   ✂️  Applied start boundary: {start_selector} (deleted everything before)")
                else:
                    print(f"   ⚠️  Start selector not found: {start_selector}")
            except Exception as e:
                print(f"   ⚠️  Error with start selector '{start_selector}': {e}")
        
        # If we have an end boundary, delete it and everything after
        if end_selector:
            try:
                end_element = soup.select_one(end_selector)
                if end_element:
                    # Delete all next siblings
                    for sibling in list(end_element.find_next_siblings()):
                        sibling.decompose()
                    # Delete the end element itself
                    end_element.decompose()
                    print(f"   ✂️  Applied end boundary: {end_selector} (deleted it and everything after)")
                else:
                    print(f"   ⚠️  End selector not found: {end_selector}")
            except Exception as e:
                print(f"   ⚠️  Error with end selector '{end_selector}': {e}")
        
        return str(soup)
    
    def _validate_boundary_cut(self, original_text: str, cut_text: str) -> Dict:
        """
        Validate if boundary cut is good.
        Returns: {'status': 'ok' | 'cut_too_much' | 'need_tighter', 'feedback': '...'}
        """
        if not self.gemini_client:
            return {'status': 'ok', 'feedback': 'No validation available'}
        
        # Prepare samples
        if len(original_text) > 8000:
            orig_sample = original_text[:4000] + "\n...\n" + original_text[-4000:]
        else:
            orig_sample = original_text
        
        if len(cut_text) > 8000:
            cut_sample = cut_text[:4000] + "\n...\n" + cut_text[-4000:]
        else:
            cut_sample = cut_text
        
        system_prompt = """You are validating if boundary cutting removed the right content.

Compare ORIGINAL (full page) vs CUT (after applying boundaries).

Your task:
1. Check if CUT removed article content → status: "cut_too_much"
2. Check if CUT still has significant noise (navigation, related articles, etc.) → status: "need_tighter"
3. If CUT looks clean (just article title + body) → status: "ok"

Return ONLY valid YAML:

```yaml
status: "ok"  # or "cut_too_much" or "need_tighter"
feedback: "Brief explanation"
```"""

        user_prompt = f"""Compare these two versions:

ORIGINAL TEXT (full page):
```
{orig_sample}
```

CUT TEXT (after boundaries):
```
{cut_sample}
```

Determine:
- If CUT removed article paragraphs/content → "cut_too_much"
- If CUT still has navigation/related articles/noise → "need_tighter"
- If CUT looks clean → "ok"

Return ONLY the YAML."""

        try:
            response = self._generate_content([system_prompt, user_prompt])
            response_text = response.text.strip()
            
            # Extract YAML
            yaml_match = re.search(r'```yaml\n(.*?)\n```', response_text, re.DOTALL)
            if yaml_match:
                yaml_text = yaml_match.group(1)
            else:
                yaml_text = response_text
            
            result = yaml.safe_load(yaml_text)
            return result
            
        except Exception as e:
            print(f"   ❌ Boundary validation error: {e}")
            return {'status': 'ok', 'feedback': 'Validation failed, assuming ok'}
    
    def apply_default_exclusions(self, html_content: str) -> str:
        """Apply default exclusions that we KNOW are not article content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove scripts, styles, and obvious non-content
        default_remove = ['script', 'style', 'noscript', 'iframe', 'embed', 'object']
        for tag in default_remove:
            for element in soup.find_all(tag):
                element.decompose()
        
        print(f"   ✂️  Applied default exclusions: {', '.join(default_remove)}")
        return str(soup)
    
    def extract_text_naive(self, html_content: str) -> str:
        """Extract all text from HTML without filtering"""
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.get_text(separator='\n', strip=True)
    
    def find_noise_categories(self, extracted_text: str, html_content: str) -> Dict:
        """
        Ask LLM to identify noise categories in extracted text and find selectors in HTML
        """
        if not self.gemini_client:
            return {'exclude_selectors': []}
        
        # Prepare samples: beginning + middle + end to see full structure
        # Text: show beginning and end (where noise often is)
        if len(extracted_text) > 15000:
            text_sample = extracted_text[:8000] + "\n\n[... middle content ...]\n\n" + extracted_text[-7000:]
        else:
            text_sample = extracted_text
        
        # HTML: show beginning + middle + end so LLM can see related articles at bottom
        if len(html_content) > 150000:
            # For large HTML: first 50K + middle 25K + last 50K
            middle_start = len(html_content) // 2 - 12500
            middle_end = len(html_content) // 2 + 12500
            html_sample = (
                html_content[:50000] + 
                "\n\n<!-- ... beginning section ... -->\n\n" +
                html_content[middle_start:middle_end] +
                "\n\n<!-- ... middle section ... -->\n\n" +
                html_content[-50000:]
            )
        else:
            html_sample = html_content
        
        system_prompt = """You are an expert at identifying non-article content in web pages.

Your task:
1. Analyze the EXTRACTED TEXT to find content that is NOT part of the main article
2. For each category of noise, search the HTML to find CSS selectors to exclude it
3. Verify selectors don't match article content (title, headings, paragraphs)

IMPORTANT: Find CATEGORIES of noise, provide ONE example per category.

Common noise categories:
- Navigation menus (top/side menus, breadcrumbs)
- Social sharing buttons ("Share on Twitter", "Post to Facebook")
- Related/recommended articles ("You might also like", "Related posts")
- Newsletter signup forms ("Subscribe", "Get updates")
- Comments section ("Comments", "Leave a reply")
- Author bio boxes (author info at the end)
- Advertisements ("Sponsored", "Ad")
- Footer links (company info, legal links)
- Call-to-action buttons

For each category:
1. Quote ONE text sample (first 50 chars) from EXTRACTED TEXT
2. Search for that text in HTML
3. Find its parent container's class/id
4. Suggest a CSS selector that matches THIS TYPE of content
5. Verify the selector doesn't match article headings or paragraphs

Return ONLY valid YAML in this format:

```yaml
noise_categories:
  - category: "social_sharing"
    text_sample: "Share on Twitter Facebook"
    selector: "[class*='share']"
    reasoning: "Matches social sharing buttons"
  - category: "newsletter"
    text_sample: "Subscribe to our newsletter"
    selector: "form[class*='newsletter']"
    reasoning: "Matches newsletter signup forms"
exclude_selectors:
  - "[class*='share']"
  - "[class*='social']"
  - "form[class*='newsletter']"
  - "[class*='comments']"
```

CRITICAL: Return ONLY the YAML, no other text."""

        user_prompt = f"""Analyze this extracted text and HTML to find noise to exclude.

EXTRACTED TEXT (what we got):
```
{text_sample}
```

HTML SOURCE (first 100k chars):
```html
{html_sample}
```

Find noise categories in the text, locate them in HTML, and provide selectors to exclude them."""

        try:
            print(f"\n🤖 ASKING GEMINI TO IDENTIFY NOISE CATEGORIES...")
            print(f"   Original text: {len(extracted_text):,} chars")
            print(f"   Text sample sent: {len(text_sample):,} chars")
            print(f"   Original HTML: {len(html_content):,} chars")
            print(f"   HTML sample sent: {len(html_sample):,} chars")
            if len(html_content) > 150000:
                print(f"   📍 HTML structure: first 50K + middle 25K + last 50K (showing end where related articles usually appear)")
            
            print(f"\n📤 SYSTEM PROMPT:")
            print("="*80)
            print(system_prompt)
            print("="*80)
            
            print(f"\n📤 USER PROMPT (first 2000 chars):")
            print("="*80)
            print(user_prompt[:2000])
            print("="*80)
            
            # Retry up to 3 times with 120s timeout budget
            max_retries = 3
            last_error = None
            for attempt in range(max_retries):
                try:
                    print(f"   Attempt {attempt + 1}/{max_retries}...")
                    response = self._generate_content([system_prompt, user_prompt])
                    break  # Success, exit retry loop
                except Exception as e:
                    last_error = e
                    error_msg = str(e)
                    if "504" in error_msg or "timeout" in error_msg.lower() or "DeadlineExceeded" in error_msg:
                        if attempt < max_retries - 1:
                            wait_time = 10 * (attempt + 1)  # 10s, 20s, 30s
                            print(f"   ⏳ Timeout error, waiting {wait_time}s before retry...")
                            import time
                            time.sleep(wait_time)
                        else:
                            print(f"   ❌ All {max_retries} attempts failed due to timeout")
                            raise Exception(f"Gemini API timeout after {max_retries} attempts") from e
                    else:
                        # Non-timeout error, don't retry
                        raise
            else:
                # All retries exhausted
                raise last_error
            response_text = response.text.strip()
            
            print(f"\n📥 GEMINI RESPONSE:")
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
            
            print(f"\n✅ PARSED NOISE CATEGORIES:")
            print(f"   Categories found: {len(config.get('noise_categories', []))}")
            for cat in config.get('noise_categories', []):
                print(f"   - {cat['category']}: {cat.get('text_sample', '')[:50]}...")
            print(f"   Total exclude selectors: {len(config.get('exclude_selectors', []))}")
            
            return config
            
        except Exception as e:
            print(f"❌ Error finding noise categories: {e}")
            import traceback
            traceback.print_exc()
            return {'exclude_selectors': []}
    
    def apply_exclusions(self, html_content: str, exclude_selectors: List[str]) -> str:
        """Apply exclusion selectors to HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        removed_count = 0
        for selector in exclude_selectors:
            try:
                elements = soup.select(selector)
                for elem in elements:
                    elem.decompose()
                    removed_count += 1
            except Exception as e:
                print(f"   ⚠️  Invalid selector '{selector}': {e}")
        
        print(f"   ✂️  Removed {removed_count} elements using {len(exclude_selectors)} selectors")
        return str(soup)
    
    def validate_extraction(self, original_text: str, cleaned_text: str, html_source: str) -> Dict:
        """
        Compare original vs cleaned text and determine if extraction is good
        """
        if not self.gemini_client:
            return {'status': 'ok', 'feedback': 'No validation available'}
        
        # Prepare samples - show more of the END where noise often hides
        if len(original_text) > 8000:
            orig_sample = original_text[:4000] + "\n...\n" + original_text[-3000:]
        else:
            orig_sample = original_text
        
        if len(cleaned_text) > 8000:
            clean_sample = cleaned_text[:4000] + "\n...\n" + cleaned_text[-3000:]
        else:
            clean_sample = cleaned_text
        
        system_prompt = """You are an expert at validating article extraction quality.

Your task:
1. Compare ORIGINAL (noisy) text with CLEANED text
2. Check if CLEANED version:
   ✓ Kept all main article content (title, paragraphs, figures, lists)
   ✓ Removed navigation, social buttons, related articles, ads, etc.
   ✗ Accidentally removed article content
   ✗ Still has noise (newsletter forms, comments, etc.)

CRITICAL: Pay special attention to the LAST 30% of the cleaned text. This is where noise often hides:
- "Related articles", "You might also like", "Readers also viewed"
- "Read more", "View more", "Explore more"
- Article cards with titles and "Read more" links
- Product recommendations
- Author bio boxes (if after the article conclusion)
- Newsletter signups at the end

If you see ANY of these patterns in the last portion of the text, mark as "needs_fixes" with specific text samples.

Return ONLY valid YAML:

```yaml
status: "ok"  # or "needs_fixes"
over_removed:  # Important content wrongly deleted (empty if none)
  - text_sample: "Figure 1: Important chart"
    description: "Article figure caption removed"
under_removed:  # Junk still present (empty if none)
  - text_sample: "Subscribe to newsletter"
    description: "Newsletter form still visible"
  - text_sample: "Readers Also Viewed These Items"
    description: "Related content section at end of article"
feedback: "Brief summary of quality"
```"""

        user_prompt = f"""Compare original extracted text with cleaned version.

ORIGINAL TEXT ({len(original_text):,} chars):
```
{orig_sample}
```

CLEANED TEXT ({len(cleaned_text):,} chars):
```
{clean_sample}
```

Is the cleaned version good? What needs to be fixed?"""

        try:
            print(f"\n🔍 VALIDATING EXTRACTION QUALITY...")
            print(f"   Original: {len(original_text):,} chars")
            print(f"   Cleaned: {len(cleaned_text):,} chars")
            print(f"   Reduction: {len(original_text) - len(cleaned_text):,} chars ({100*(len(original_text)-len(cleaned_text))//len(original_text) if original_text else 0}%)")
            
            # Retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    print(f"   Validation attempt {attempt + 1}/{max_retries}...")
                    response = self._generate_content([system_prompt, user_prompt])
                    break
                except Exception as e:
                    if "504" in str(e) or "timeout" in str(e).lower():
                        if attempt < max_retries - 1:
                            import time
                            time.sleep(10 * (attempt + 1))
                        else:
                            raise Exception(f"Validation timeout after {max_retries} attempts") from e
                    else:
                        raise
            
            response_text = response.text.strip()
            
            print(f"\n📥 VALIDATION RESPONSE:")
            print("="*80)
            print(response_text)
            print("="*80)
            
            # Extract YAML
            yaml_match = re.search(r'```yaml\n(.*?)\n```', response_text, re.DOTALL)
            if yaml_match:
                yaml_text = yaml_match.group(1)
            else:
                yaml_text = response_text
            
            result = yaml.safe_load(yaml_text)
            
            print(f"\n✅ VALIDATION RESULT: {result.get('status', 'unknown')}")
            print(f"   Feedback: {result.get('feedback', 'N/A')}")
            if result.get('over_removed'):
                print(f"   ⚠️  Over-removed: {len(result['over_removed'])} items")
            if result.get('under_removed'):
                print(f"   ⚠️  Under-removed: {len(result['under_removed'])} items")
            
            return result
            
        except Exception as e:
            print(f"❌ Validation error: {e}")
            import traceback
            traceback.print_exc()
            return {'status': 'unknown', 'feedback': str(e)}
    
    def refine_selectors(self, html_source: str, current_excludes: List[str], validation: Dict) -> Dict:
        """Refine selectors based on validation feedback"""
        if not self.gemini_client:
            return {'final_exclude_list': current_excludes}
        
        # Show beginning + end of HTML so LLM can see related articles at bottom
        if len(html_source) > 100000:
            html_sample = html_source[:50000] + "\n\n<!-- ... middle ... -->\n\n" + html_source[-50000:]
        else:
            html_sample = html_source
        
        system_prompt = """You are an expert at refining CSS selectors for content extraction.

Your task:
1. Review current exclusion selectors
2. Based on feedback, determine which selectors to add/remove
3. Return updated selector list

IMPORTANT:
- If content was OVER-REMOVED: Remove the selector causing it
- If noise is UNDER-REMOVED: Add selector to exclude it
- Verify new selectors in HTML source
- Keep selectors specific (avoid too broad matches)

Return ONLY valid YAML:

```yaml
add_selectors:  # New selectors to exclude noise
  - "form.newsletter-signup"
remove_selectors:  # Selectors that removed content
  - "div.content"
final_exclude_list:  # Complete updated list
  - "nav"
  - "footer"
  - "form.newsletter-signup"
reasoning: "Brief explanation of changes"
```"""

        user_prompt = f"""Refine exclusion selectors based on validation feedback.

CURRENT EXCLUDE SELECTORS:
```yaml
{yaml.dump(current_excludes)}
```

VALIDATION FEEDBACK:
```yaml
over_removed: {yaml.dump(validation.get('over_removed', []))}
under_removed: {yaml.dump(validation.get('under_removed', []))}
```

HTML SAMPLE (first 50k):
```html
{html_sample}
```

What selectors should we add or remove?"""

        try:
            print(f"\n🔧 REFINING SELECTORS...")
            
            # Retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    print(f"   Refinement attempt {attempt + 1}/{max_retries}...")
                    response = self._generate_content([system_prompt, user_prompt])
                    break
                except Exception as e:
                    if "504" in str(e) or "timeout" in str(e).lower():
                        if attempt < max_retries - 1:
                            import time
                            time.sleep(10 * (attempt + 1))
                        else:
                            raise Exception(f"Refinement timeout after {max_retries} attempts") from e
                    else:
                        raise
            
            response_text = response.text.strip()
            
            print(f"\n📥 REFINEMENT RESPONSE:")
            print("="*80)
            print(response_text)
            print("="*80)
            
            # Extract YAML
            yaml_match = re.search(r'```yaml\n(.*?)\n```', response_text, re.DOTALL)
            if yaml_match:
                yaml_text = yaml_match.group(1)
            else:
                yaml_text = response_text
            
            result = yaml.safe_load(yaml_text)
            
            print(f"\n✅ REFINEMENT RESULT:")
            print(f"   Add: {len(result.get('add_selectors', []))} selectors")
            print(f"   Remove: {len(result.get('remove_selectors', []))} selectors")
            print(f"   Final total: {len(result.get('final_exclude_list', []))} selectors")
            print(f"   Reasoning: {result.get('reasoning', 'N/A')}")
            
            return result
            
        except Exception as e:
            print(f"❌ Refinement error: {e}")
            import traceback
            traceback.print_exc()
            return {'final_exclude_list': current_excludes}
    
    def learn_from_html(self, url: str, html_content: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Main inverted learning flow
        """
        print(f"\n{'='*80}")
        print(f"🧠 INVERTED LEARNING FOR: {url}")
        print(f"{'='*80}")
        print(f"HTML size: {len(html_content):,} characters\n")
        
        # Step 1: Apply default exclusions
        print(f"STEP 1: APPLY DEFAULT EXCLUSIONS")
        print("-"*80)
        html_cleaned = self.apply_default_exclusions(html_content)
        print(f"   Result: {len(html_content):,} → {len(html_cleaned):,} chars\n")
        
        # Step 2: Extract text naively
        print(f"STEP 2: EXTRACT ALL TEXT NAIVELY")
        print("-"*80)
        original_text = self.extract_text_naive(html_cleaned)
        print(f"   Extracted: {len(original_text):,} characters")
        print(f"   First 500 chars: {original_text[:500]}...\n")
        
        # Step 3: Iteratively find and refine article boundaries (up to 3 iterations)
        print(f"STEP 3: IDENTIFY & REFINE ARTICLE BOUNDARIES")
        print("-"*80)
        
        article_start_selector = None
        article_end_selector = None
        html_for_boundary_detection = html_cleaned
        boundary_iteration = 0
        max_boundary_iterations = 3
        
        while boundary_iteration < max_boundary_iterations:
            boundary_iteration += 1
            print(f"\n   Boundary detection attempt {boundary_iteration}/{max_boundary_iterations}")
            
            # Ask LLM to find boundaries
            boundaries = self.find_article_boundaries(original_text, html_for_boundary_detection)
            
            if not boundaries.get('has_boundaries'):
                print(f"   No clear boundaries found, will use body + exclusions\n")
                break
            
            # Extract proposed boundaries
            article_start = boundaries.get('article_start', {})
            article_end = boundaries.get('article_end', {})
            proposed_start = article_start.get('selector')
            proposed_end = article_end.get('selector')
            
            print(f"   Proposed start: {proposed_start}")
            print(f"   Proposed end: {proposed_end}")
            
            # Apply boundaries and extract
            html_with_boundaries = self.extract_with_boundaries(html_for_boundary_detection, proposed_start, proposed_end)
            boundary_extracted_text = self.extract_text_naive(html_with_boundaries)
            
            print(f"   Result: {len(boundary_extracted_text):,} chars")
            
            # Validate: compare original vs boundary-cut version
            print(f"   Validating boundary cut...")
            validation = self._validate_boundary_cut(original_text, boundary_extracted_text)
            
            if validation.get('status') == 'ok':
                # Boundaries are good!
                article_start_selector = proposed_start
                article_end_selector = proposed_end
                print(f"   ✅ Boundaries validated successfully\n")
                break
            elif validation.get('status') == 'cut_too_much':
                # We removed article content - boundaries are wrong, try again with original HTML
                print(f"   ⚠️  Cut too much: {validation.get('feedback')}")
                print(f"   Retrying with original HTML...\n")
                # Keep html_for_boundary_detection as is (original)
                continue
            elif validation.get('status') == 'need_tighter':
                # Still has noise - use the cut version for next iteration
                print(f"   ⚠️  Need tighter boundaries: {validation.get('feedback')}")
                print(f"   Retrying with cut HTML...\n")
                html_for_boundary_detection = html_with_boundaries
                continue
            else:
                # Unknown status, stop
                print(f"   ⚠️  Unknown validation status: {validation.get('status')}\n")
                break
        
        if article_start_selector or article_end_selector:
            print(f"   Final boundaries:")
            print(f"      Start: {article_start_selector or 'None'}")
            print(f"      End: {article_end_selector or 'None'}\n")
        else:
            print(f"   No boundaries found, will use body + exclusions\n")
        
        # Step 4: Find noise categories
        print(f"STEP 4: IDENTIFY NOISE CATEGORIES")
        print("-"*80)
        noise_result = self.find_noise_categories(original_text, html_cleaned)
        exclude_selectors = noise_result.get('exclude_selectors', [])
        
        if not exclude_selectors:
            print(f"❌ No exclusion selectors identified\n")
            return False, None, "Failed to identify noise categories"
        
        print(f"   Found {len(exclude_selectors)} exclusion selectors\n")
        
        # Step 5: Apply boundaries + exclusions
        print(f"STEP 5: APPLY BOUNDARIES + EXCLUSIONS")
        print("-"*80)
        
        # Apply boundaries first (if any)
        if article_start_selector or article_end_selector:
            html_with_boundaries = self.extract_with_boundaries(html_cleaned, article_start_selector, article_end_selector)
        else:
            html_with_boundaries = html_cleaned
        
        # Then apply exclusions within the boundaries
        html_filtered = self.apply_exclusions(html_with_boundaries, exclude_selectors)
        cleaned_text = self.extract_text_naive(html_filtered)
        print(f"   Cleaned text: {len(cleaned_text):,} characters\n")
        
        # Step 6: Validate
        print(f"STEP 6: VALIDATE EXTRACTION")
        print("-"*80)
        validation = self.validate_extraction(original_text, cleaned_text, html_cleaned)
        
        # Step 7: Noise reduction refinement (max 3 iterations)
        iteration = 0
        max_iterations = 3
        
        while validation.get('status') == 'needs_fixes' and iteration < max_iterations:
            iteration += 1
            print(f"\nITERATION {iteration}/{max_iterations}: REFINING EXCLUSION SELECTORS")
            print("-"*80)
            
            refinement = self.refine_selectors(html_cleaned, exclude_selectors, validation)
            exclude_selectors = refinement.get('final_exclude_list', exclude_selectors)
            
            # Re-apply
            html_with_boundaries = self.extract_with_boundaries(html_cleaned, article_start_selector, article_end_selector) if (article_start_selector or article_end_selector) else html_cleaned
            html_filtered = self.apply_exclusions(html_with_boundaries, exclude_selectors)
            cleaned_text = self.extract_text_naive(html_filtered)
            
            print(f"\nRE-VALIDATION:")
            print("-"*80)
            validation = self.validate_extraction(original_text, cleaned_text, html_cleaned)
        
        # Step 8: Generate config
        print(f"\nSTEP 8: GENERATE CONFIG")
        print("-"*80)
        
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Build article_content config
        article_content_config = {}
        
        # Use boundary selector if available, otherwise use body
        if article_start_selector:
            article_content_config['selector'] = article_start_selector
            print(f"   Using boundary selector: {article_start_selector}")
        else:
            article_content_config['selector'] = 'body'
            print(f"   Using default selector: body")
        
        # Always add exclude_selectors (works inside boundaries too)
        article_content_config['exclude_selectors'] = exclude_selectors
        
        # Add end boundary if found
        if article_end_selector:
            article_content_config['truncate_after'] = article_end_selector
            print(f"   Truncate after: {article_end_selector}")
        
        config = {
            'domain': domain,
            'extraction': {
                'article_content': article_content_config
            },
            'notes': f'Inverted learning approach. Boundaries: {"yes" if article_start_selector else "no"}. Validation: {validation.get("status")}'
        }
        
        print(f"   Domain: {domain}")
        print(f"   Exclude selectors: {len(exclude_selectors)}")
        print(f"   Validation status: {validation.get('status')}")
        print(f"\n✅ LEARNING COMPLETE\n")
        
        return True, config, None


# Convenience function
def learn_inverted(url: str, html_content: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """Convenience function for inverted learning"""
    learner = InvertedLearner(use_gemini=True)
    return learner.learn_from_html(url, html_content)

