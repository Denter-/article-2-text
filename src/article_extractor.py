#!/usr/bin/env python3
"""
Article Extractor for ForEntrepreneurs.com
Automatically converts articles to text-only Markdown with AI-powered image descriptions
Now with Google Gemini Vision API support!
"""

import re
import html
import json
import sys
import argparse
import os
import time
import urllib.request
import logging
import asyncio
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime
import subprocess

# Import site registry for self-learning
try:
    from .site_registry import SiteRegistry
    from .extraction_engine import ExtractionEngine
except ImportError:
    # Fallback for direct execution
    import site_registry
    import extraction_engine
    SiteRegistry = site_registry.SiteRegistry
    ExtractionEngine = extraction_engine.ExtractionEngine

# Suppress gRPC/ALTS warnings from Google APIs
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'

# Suppress Pydantic warnings about field shadowing
import warnings
warnings.filterwarnings('ignore', message='Field name .* shadows an attribute')

# Optional Gemini support
GEMINI_AVAILABLE = False
try:
    from google import genai
    from google.genai.types import GenerateContentConfig, ThinkingConfig
    from PIL import Image
    from dotenv import load_dotenv
    load_dotenv()
    GEMINI_AVAILABLE = True
except ImportError:
    pass


class ArticleExtractor:
    def __init__(self, output_dir="results", use_gemini=False, gemini_api_key=None, log_file=None, force_renew=False):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.use_gemini = use_gemini and GEMINI_AVAILABLE
        self.gemini_client = None
        self.force_renew = force_renew
        
        # Setup logging
        self.setup_logging(log_file)
        
        # Initialize site registry for self-learning
        self.site_registry = SiteRegistry(use_gemini=use_gemini) if use_gemini else None
        self.extraction_engine = ExtractionEngine()
        
        if self.use_gemini:
            if not gemini_api_key:
                gemini_api_key = os.getenv('GEMINI_API_KEY')
            
            if not gemini_api_key:
                print("⚠️  Warning: GEMINI_API_KEY not found, falling back to context-based descriptions")
                self.use_gemini = False
            else:
                try:
                    self.gemini_client = genai.Client(api_key=gemini_api_key)
                    print("✓ Gemini Vision API enabled (2.5 Flash - thinking disabled)")
                except Exception as e:
                    print(f"⚠️  Warning: Failed to initialize Gemini: {e}")
                    print("   Falling back to context-based descriptions")
                    self.use_gemini = False
    
    def setup_logging(self, log_file=None, verbose=False):
        """Setup logging to file and console"""
        # Create logs directory
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # Generate log filename if not provided
        if not log_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = log_dir / f'extraction_{timestamp}.log'
        else:
            log_file = Path(log_file)
        
        # Configure logging
        self.logger = logging.getLogger('ArticleExtractor')
        self.logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG if verbose else logging.WARNING)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info(f"Logging initialized: {log_file} | verbose={verbose}")
        
    def download_article(self, url):
        """Download article HTML using curl"""
        print(f"📥 Downloading article from {url}...")
        self.logger.info(f"Downloading article from {url}")
        result = subprocess.run(
            ['curl', '-s', url],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            self.logger.error(f"Failed to download article: {result.stderr}")
            raise Exception(f"Failed to download article: {result.stderr}")
        self.logger.info(f"Downloaded {len(result.stdout)} bytes")
        return result.stdout
    
    def download_image(self, url, output_path):
        """Download image from URL"""
        try:
            urllib.request.urlretrieve(url, output_path)
            if output_path.stat().st_size < 100:
                return False
            return True
        except Exception:
            return False
    
    def generate_gemini_description(self, image_url, context_before, context_after):
        """Generate image description using Gemini Vision API (synchronous wrapper)"""
        if not self.use_gemini or not self.gemini_client:
            return None
        
        # This is now just a wrapper for the async version
        # Used when called individually (shouldn't happen in normal flow)
        return asyncio.run(self._generate_gemini_description_async(image_url, context_before, context_after))
    
    async def _generate_gemini_description_async(self, image_url, context_before, context_after, max_retries=3):
        """Generate image description using Gemini Vision API (async with retry logic)"""
        if not self.use_gemini or not self.gemini_client:
            return None
        
        # Download image to temp location
        temp_dir = Path('/tmp/article_extractor_images')
        temp_dir.mkdir(exist_ok=True)
        
        image_name = image_url.split('/')[-1].split('?')[0]
        if not any(image_name.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
            image_name += '.png'
        
        image_path = temp_dir / image_name
        
        # Download
        if not self.download_image(image_url, image_path):
            return None
        
        # Retry logic
        last_error = None
        for attempt in range(max_retries):
            try:
                # Load image
                img = Image.open(image_path)
                
                # Create comprehensive prompt
                system_context = """You are an expert at analyzing business charts, diagrams, and visualizations for SaaS metrics and business analytics.

Your task is to create detailed, accessible text descriptions that will replace images in a text-only document.

IMPORTANT: SKIP the following types of images by responding with exactly "SKIP: [reason]":
- Navigation elements (buttons, menus, breadcrumbs, headers, footers)
- UI elements (icons, logos, decorative graphics, social media buttons)
- Call-to-action buttons or link graphics
- Page layout elements (dividers, backgrounds, borders)
- Non-content images

ONLY describe content-relevant visualizations such as:
- Charts (Line, Bar, Area, Pie, etc.)
- Graphs and plots
- Tables with data
- Diagrams (flowcharts, schematics, concept maps)
- Formulas and equations
- Screenshots of actual data/dashboards (not UI chrome)
- Infographics with business information

For valid content visualizations, the description MUST:
1. Start by identifying the TYPE (Line Graph, Bar Chart, Area Chart, Table, Diagram, Formula, Dashboard, etc.)
   - Be specific: "Line Graph" not just "Graph"
   - For cumulative metrics, note this explicitly
2. Describe what is being measured or visualized
3. Explain the key patterns, trends, or insights visible
4. Include specific data points, axes labels, and important values when present
5. Be comprehensive enough for someone listening via text-to-speech to fully understand

CRITICAL FORMATTING RULES:
- Write in the SAME LANGUAGE as the article text
- Do NOT include image URLs or file paths in your description
- Do NOT use phrases like "the image shows" - describe directly
- Write in clear, professional language

The surrounding article context is provided to help you understand what the visualization illustrates."""

                user_prompt = f"""Analyze this image and determine if it's a content-relevant visualization or a UI/navigation element.

ARTICLE CONTEXT BEFORE:
{context_before[:800]}

ARTICLE CONTEXT AFTER:
{context_after[:800]}

If it's a UI element, button, logo, or navigation graphic, respond with "SKIP: [brief reason]".

If it's a business chart, graph, table, diagram, or formula, provide a comprehensive description.
IMPORTANT: Write in the same language as the article text above. Do NOT include any URLs or image paths."""

                full_prompt = system_context + "\n\n" + user_prompt
                
                # Generate description using new SDK (run in executor to avoid blocking)
                loop = asyncio.get_event_loop()
                
                def call_gemini():
                    config = GenerateContentConfig(
                        temperature=0.1,
                        top_p=0.95,
                        top_k=40,
                        max_output_tokens=8192,
                        thinking_config=ThinkingConfig(thinking_budget=0)
                    )
                    # New SDK requires image to be part of contents list
                    return self.gemini_client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[full_prompt, img],
                        config=config
                    )
                
                response = await loop.run_in_executor(None, call_gemini)
                description = response.text.strip()
                
                # Clean up
                image_path.unlink(missing_ok=True)
                
                # Check if AI decided to skip this image
                if description.startswith("SKIP:"):
                    self.logger.info(f"Skipped UI element: {image_url}")
                    return f"[UI Element - {description[5:].strip()}]"
                
                self.logger.info(f"Generated description for {image_url}: {len(description)} chars")
                return description
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for {image_url}: {e}")
                
                if attempt < max_retries - 1:
                    # Wait before retry (exponential backoff)
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                else:
                    # Final attempt failed
                    self.logger.error(f"All {max_retries} attempts failed for {image_url}: {last_error}")
                    print(f"   ⚠️  Gemini API error after {max_retries} retries: {last_error}")
                    image_path.unlink(missing_ok=True)
                    return None
        
        return None
    
    async def _process_images_parallel(self, images_data):
        """Process all images in parallel with staggered start"""
        if not self.use_gemini or not images_data:
            return {}
        
        print(f"🤖 Processing {len(images_data)} images in parallel with Gemini Vision API...")
        
        tasks = []
        for i, img_data in enumerate(images_data):
            # Create task
            task = self._generate_gemini_description_async(
                img_data['src'],
                img_data['context_before'],
                img_data['context_after']
            )
            tasks.append(task)
            
            # Stagger the start of requests (0.1s delay between each)
            if i < len(images_data) - 1:
                await asyncio.sleep(0.1)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build a dictionary mapping image URLs to descriptions
        descriptions_map = {}
        for img_data, result in zip(images_data, results):
            if isinstance(result, Exception):
                self.logger.error(f"Failed to process {img_data['src']}: {result}")
                descriptions_map[img_data['src']] = None
            else:
                descriptions_map[img_data['src']] = result
        
        return descriptions_map
    
    def extract_metadata(self, html_content):
        """Extract article metadata (title, author, date)"""
        metadata = {}
        
        # Extract title
        title_match = re.search(r'<meta property="og:title" content="([^"]+)"', html_content)
        if title_match:
            metadata['title'] = html.unescape(title_match.group(1))
        else:
            # Fallback to page title
            title_match = re.search(r'<title>([^<]+)</title>', html_content)
            if title_match:
                metadata['title'] = html.unescape(title_match.group(1).split(' - ')[0])
        
        # Extract author
        author_match = re.search(r'"author".*?"name":"([^"]+)"', html_content)
        if author_match:
            metadata['author'] = html.unescape(author_match.group(1))
        
        # Extract dates
        date_pub = re.search(r'"datePublished":"([^"]+)"', html_content)
        date_mod = re.search(r'"dateModified":"([^"]+)"', html_content)
        
        if date_pub:
            metadata['date_published'] = date_pub.group(1).split('T')[0]
        if date_mod:
            metadata['date_modified'] = date_mod.group(1).split('T')[0]
        
        return metadata
    
    def extract_article_content(self, html_content, url=None, requires_browser=False):
        """Extract main article content from HTML using site registry"""
        
        # Try site registry first (self-learning)
        if self.site_registry and url:
            domain = self.site_registry.get_domain_from_url(url)
            
            # If force_renew, delete existing config to trigger re-learning
            if self.force_renew:
                config_path = self.site_registry.get_config_path(domain)
                if config_path.exists():
                    config_path.unlink()
                    self.logger.info(f"🗑️  Deleted existing config for {domain} (force-renew)")
                config = None
            else:
                # Load existing config or learn new one
                config = self.site_registry.load_config(domain)
            
            if not config and self.use_gemini:
                # Learn from this site
                success, config, error = self.site_registry.learn_from_html(
                    url, html_content, force=self.force_renew, requires_browser=requires_browser
                )
                if not success:
                    self.logger.warning(f"Failed to learn site structure: {error}")
                    # Fall through to fallback strategies
            
            # Try extraction with config
            if config:
                content = self.extraction_engine.extract_article_html(html_content, config)
                if content:
                    return content
        
        # No fallback - if learning failed, we should know about it
        raise Exception(f"Could not extract article content. Site template learning failed or no config available for {url}")
    
    def extract_images(self, content):
        """Extract all images with their context"""
        images = []
        
        for img_match in re.finditer(r'<img[^>]*>', content):
            img_tag = img_match.group(0)
            
            src = re.search(r'src=["\']([^"\']+)["\']', img_tag)
            alt = re.search(r'alt=["\']([^"\']*)["\']', img_tag)
            title = re.search(r'title=["\']([^"\']*)["\']', img_tag)
            
            # Get surrounding text for context (500 chars before and after)
            start = max(0, img_match.start() - 500)
            end = min(len(content), img_match.end() + 500)
            context_before = content[start:img_match.start()]
            context_after = content[img_match.end():end]
            
            # Clean HTML from context
            context_before_text = re.sub(r'<[^>]+>', ' ', context_before)
            context_before_text = html.unescape(context_before_text).strip()
            context_after_text = re.sub(r'<[^>]+>', ' ', context_after)
            context_after_text = html.unescape(context_after_text).strip()
            
            if src:
                images.append({
                    'src': src.group(1),
                    'alt': alt.group(1) if alt else '',
                    'title': title.group(1) if title else '',
                    'position': img_match.start(),
                    'context_before': context_before_text,
                    'context_after': context_after_text
                })
        
        return images
    
    def generate_image_description(self, img_data, img_index, total_images, gemini_desc=None):
        """Generate a description for an image (using pre-generated Gemini description if available)"""
        
        # Use pre-generated Gemini description if provided
        if gemini_desc:
            # Format nicely
            desc = f"\n\n**[AI-Generated Image Description {img_index + 1}/{total_images}]**\n\n"
            desc += gemini_desc
            desc += f"\n\n*[Original image: {img_data['src']}]*\n\n"
            return desc
        
        # Fallback to context-based description
        desc_parts = []
        
        if img_data['alt'] and img_data['alt'].lower() not in ['image', '', 'img']:
            desc_parts.append(f"Alt text: {img_data['alt']}")
        
        if img_data['title'] and img_data['title'].lower() not in ['image', '', 'img']:
            desc_parts.append(f"Title: {img_data['title']}")
        
        # Analyze context for clues
        context = (img_data['context_before'] + ' ' + img_data['context_after']).lower()
        
        # Detect common visualization types
        viz_type = "Visualization"
        if any(word in context for word in ['chart', 'graph', 'plot', 'curve']):
            viz_type = "Chart"
        elif any(word in context for word in ['diagram', 'flow', 'model']):
            viz_type = "Diagram"
        elif any(word in context for word in ['table', 'matrix']):
            viz_type = "Table"
        elif any(word in context for word in ['dashboard', 'metrics']):
            viz_type = "Dashboard"
        elif any(word in context for word in ['screenshot', 'example']):
            viz_type = "Screenshot"
        
        # Build description
        description = f"\n\n**[{viz_type} {img_index + 1}/{total_images}]**\n\n"
        
        if desc_parts:
            description += " | ".join(desc_parts) + "\n\n"
        
        description += f"Context: {img_data['context_before'][:400]}...\n\n"
        description += f"*[For full details, see original image: {img_data['src']}]*\n\n"
        
        return description
    
    def clean_html_entities(self, text):
        """Clean HTML entities"""
        text = html.unescape(text)
        text = text.replace('\u2013', '-')
        text = text.replace('\u2014', '--')
        text = text.replace('\u2019', "'")
        text = text.replace('\u201c', '"')
        text = text.replace('\u201d', '"')
        text = text.replace('\u2026', '...')
        return text
    
    def html_to_markdown(self, html_content, images_data, gemini_descriptions=None):
        """Convert HTML to Markdown with image descriptions"""
        text = html_content
        
        # First, replace images with placeholders
        for i, img in enumerate(sorted(images_data, key=lambda x: x['position'])):
            placeholder = f"___IMAGE_{i}___"
            img_pattern = re.escape(img['src'].split('?')[0])
            text = re.sub(
                f'<img[^>]*src=["\'][^"\']*{img_pattern}[^"\']*["\'][^>]*>',
                placeholder,
                text,
                count=1
            )
        
        # Remove navigation, scripts, styles
        text = re.sub(r'<(script|style|nav|form)[^>]*>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<div[^>]*class="[^"]*search[^"]*"[^>]*>.*?</div>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Convert HTML to Markdown
        # Headers
        text = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1\n\n', text, flags=re.DOTALL)
        text = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1\n\n', text, flags=re.DOTALL)
        text = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1\n\n', text, flags=re.DOTALL)
        text = re.sub(r'<h4[^>]*>(.*?)</h4>', r'#### \1\n\n', text, flags=re.DOTALL)
        
        # Links
        text = re.sub(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.DOTALL)
        
        # Bold/Italic
        text = re.sub(r'<(strong|b)[^>]*>(.*?)</\1>', r'**\2**', text, flags=re.DOTALL)
        text = re.sub(r'<(em|i)[^>]*>(.*?)</\1>', r'*\2*', text, flags=re.DOTALL)
        
        # Lists
        text = re.sub(r'<ul[^>]*>', '\n', text)
        text = re.sub(r'</ul>', '\n', text)
        text = re.sub(r'<ol[^>]*>', '\n', text)
        text = re.sub(r'</ol>', '\n', text)
        text = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', text, flags=re.DOTALL)
        
        # Blockquotes
        def format_blockquote(match):
            content = match.group(1).strip()
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            return '\n> ' + '\n> '.join(lines) + '\n\n'
        text = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', format_blockquote, text, flags=re.DOTALL)
        
        # Paragraphs
        text = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', text, flags=re.DOTALL)
        
        # Break tags
        text = re.sub(r'<br\s*/?>', '\n', text)
        
        # Remove remaining HTML
        text = re.sub(r'<[^>]+>', '', text)
        
        # Clean entities
        text = self.clean_html_entities(text)
        
        # Replace image placeholders with descriptions
        for i, img in enumerate(sorted(images_data, key=lambda x: x['position'])):
            placeholder = f"___IMAGE_{i}___"
            # Get pre-generated Gemini description if available
            gemini_desc = None
            if gemini_descriptions and img['src'] in gemini_descriptions:
                gemini_desc = gemini_descriptions[img['src']]
            description = self.generate_image_description(img, i, len(images_data), gemini_desc)
            text = text.replace(placeholder, description)
        
        # Clean up whitespace
        text = re.sub(r'\n\n\n+', '\n\n', text)
        text = re.sub(r'  +', ' ', text)
        text = re.sub(r'(?<=\n) +', '', text)
        
        return text.strip()
    
    def create_markdown_file(self, url, metadata, content, images):
        """Create final Markdown file"""
        # Generate filename from title
        title = metadata.get('title', 'article')
        filename = re.sub(r'[^\w\s-]', '', title)
        filename = re.sub(r'[-\s]+', '_', filename)
        filename = filename[:100] + '.md'
        
        # Create header
        header = f"# {metadata.get('title', 'Article')}\n\n"
        
        if metadata.get('author'):
            header += f"**Author:** {metadata['author']}  \n"
        
        header += f"**Source:** [{urlparse(url).netloc}]({url})  \n"
        
        if metadata.get('date_published'):
            header += f"**Published:** {metadata['date_published']}  \n"
        
        if metadata.get('date_modified'):
            header += f"**Last Modified:** {metadata['date_modified']}  \n"
        
        header += f"\n**Images:** {len(images)} visualizations"
        if self.use_gemini:
            header += " (AI-generated descriptions)"
        else:
            header += " (context-based descriptions)"
        header += "  \n"
        
        header += "\n*Note: This is a text-only version. All charts and images have been replaced with detailed text descriptions.*\n"
        header += "\n---\n\n"
        
        # Combine
        full_content = header + content
        
        # Remove duplicate title if present
        full_content = re.sub(r'---\n+# ' + re.escape(metadata.get('title', '')) + r'[^\n]*\n+', '---\n\n', full_content)
        
        # Save
        output_path = self.output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        return output_path
    
    def process_article(self, url):
        """Main processing pipeline"""
        try:
            # Download with curl first (fast)
            html_content = self.download_article(url)
            
            # Smart detection: Check if content looks dynamic/incomplete
            requires_browser = False
            if self.site_registry and self.use_gemini:
                # Check the site config first
                domain = self.site_registry.get_domain_from_url(url)
                config = self.site_registry.load_config(domain)
                
                if config and config.get('requires_browser'):
                    # Config says we need browser for this site
                    requires_browser = True
                    print("   ℹ️  Site config indicates dynamic content")
                elif not config:
                    # No config yet - ask LLM to check the HTML
                    print("🔍 Checking if content requires JavaScript...")
                    is_dynamic, reason = self.site_registry.check_if_dynamic_content(html_content, url)
                    requires_browser = is_dynamic
            
            # Re-fetch with browser if needed
            if requires_browser:
                print("🌐 Re-fetching with headless browser...")
                success, browser_html, error = self.site_registry.fetch_with_browser(url)
                if success:
                    html_content = browser_html
                else:
                    print(f"   ⚠️  Browser fetch failed: {error}")
                    print("   📄 Continuing with curl version...")
            
            # Extract components
            print("📝 Extracting metadata...")
            metadata = self.extract_metadata(html_content)
            
            print("📄 Extracting article content...")
            article_html = self.extract_article_content(html_content, url=url, requires_browser=requires_browser)
            
            print("🖼️  Extracting images...")
            images = self.extract_images(article_html)
            print(f"   Found {len(images)} images")
            
            # Process images in parallel with Gemini if enabled
            gemini_descriptions = {}
            if self.use_gemini and images:
                start_time = time.time()
                gemini_descriptions = asyncio.run(self._process_images_parallel(images))
                elapsed = time.time() - start_time
                successful = sum(1 for desc in gemini_descriptions.values() if desc is not None)
                print(f"   ✓ Processed {successful}/{len(images)} images in {elapsed:.1f}s")
            
            print("🔄 Converting to Markdown...")
            markdown_content = self.html_to_markdown(article_html, images, gemini_descriptions)
            
            print("💾 Creating Markdown file...")
            output_path = self.create_markdown_file(url, metadata, markdown_content, images)
            
            print(f"✅ Success! Created: {output_path}")
            print(f"   Words: {len(markdown_content.split())}")
            print(f"   Images processed: {len(images)}")
            if self.use_gemini:
                successful = sum(1 for desc in gemini_descriptions.values() if desc is not None)
                print(f"   AI descriptions: {successful}/{len(images)}")
            
            return output_path
            
        except Exception as e:
            print(f"❌ Error processing {url}: {str(e)}")
            self.logger.error(f"Error processing {url}: {str(e)}", exc_info=True)
            return None


def main():
    parser = argparse.ArgumentParser(
        description='Extract articles to text-only Markdown with AI-powered image descriptions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single article with AI descriptions
  %(prog)s --gemini https://www.forentrepreneurs.com/saas-metrics-2/
  
  # Multiple articles
  %(prog)s --gemini https://example.com/article1 https://example.com/article2
  
  # Batch from file
  %(prog)s --gemini --file urls.txt
  
  # Without AI (context-based descriptions, free)
  %(prog)s https://example.com/article
  
  # Custom output directory
  %(prog)s --gemini --output ./articles https://example.com/article

Note: Gemini Vision API requires GEMINI_API_KEY in environment or .env file
      Get your key from: https://makersuite.google.com/app/apikey
        """
    )
    
    parser.add_argument('urls', nargs='*', help='Article URLs to process')
    parser.add_argument('-f', '--file', help='File containing URLs (one per line)')
    parser.add_argument('-o', '--output', default='results', help='Output directory (default: ./results)')
    parser.add_argument('--gemini', action='store_true', help='Use Gemini Vision API for image descriptions (requires API key)')
    parser.add_argument('--api-key', help='Gemini API key (or set GEMINI_API_KEY environment variable)')
    parser.add_argument('--force-renew', action='store_true', help='Force re-learning of site extraction rules (ignores existing config)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose console logging (debug level)')
    
    args = parser.parse_args()
    
    # Check Gemini availability
    if args.gemini and not GEMINI_AVAILABLE:
        print("❌ Error: Gemini support requires additional packages")
        print("\nInstall them with:")
        print("  pip install google-generativeai pillow python-dotenv")
        sys.exit(1)
    
    # Collect URLs
    urls = list(args.urls) if args.urls else []
    
    if args.file:
        try:
            with open(args.file, 'r') as f:
                file_urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                urls.extend(file_urls)
        except Exception as e:
            print(f"❌ Error reading file {args.file}: {e}")
            sys.exit(1)
    
    if not urls:
        parser.print_help()
        sys.exit(1)
    
    # Process articles
    extractor = ArticleExtractor(
        output_dir=args.output,
        use_gemini=args.gemini,
        gemini_api_key=args.api_key,
        force_renew=args.force_renew
    )
    # Reconfigure logging with verbosity
    extractor.setup_logging(verbose=args.verbose)
    
    print(f"\n🚀 Processing {len(urls)} article(s)...")
    if args.gemini:
        print("🤖 AI-powered image descriptions enabled (Gemini Vision API)")
    else:
        print("📝 Using context-based image descriptions (free)")
    print()
    
    results = []
    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] Processing: {url}")
        print("-" * 60)
        result = extractor.process_article(url)
        results.append((url, result))
        print()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    successful = sum(1 for _, r in results if r)
    failed = len(results) - successful
    
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    
    if successful > 0:
        print(f"\n📁 Output directory: {Path(args.output).absolute()}")
        print("\n✅ Successfully processed:")
        for url, path in results:
            if path:
                print(f"   • {path.name}")


if __name__ == '__main__':
    main()

