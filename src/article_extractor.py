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
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime
import subprocess

# Suppress gRPC/ALTS warnings from Google APIs
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'

# Optional Gemini support
GEMINI_AVAILABLE = False
try:
    import google.generativeai as genai
    from PIL import Image
    from dotenv import load_dotenv
    load_dotenv()
    GEMINI_AVAILABLE = True
except ImportError:
    pass


class ArticleExtractor:
    def __init__(self, output_dir=".", use_gemini=False, gemini_api_key=None, log_file=None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.use_gemini = use_gemini and GEMINI_AVAILABLE
        self.gemini_model = None
        
        # Setup logging
        self.setup_logging(log_file)
        
        if self.use_gemini:
            if not gemini_api_key:
                gemini_api_key = os.getenv('GEMINI_API_KEY')
            
            if not gemini_api_key:
                print("⚠️  Warning: GEMINI_API_KEY not found, falling back to context-based descriptions")
                self.use_gemini = False
            else:
                try:
                    genai.configure(api_key=gemini_api_key)
                    self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')
                    print("✓ Gemini Vision API enabled")
                except Exception as e:
                    print(f"⚠️  Warning: Failed to initialize Gemini: {e}")
                    print("   Falling back to context-based descriptions")
                    self.use_gemini = False
    
    def setup_logging(self, log_file=None):
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
        self.logger.setLevel(logging.INFO)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        
        # Console handler (only warnings and errors)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info(f"Logging initialized: {log_file}")
        
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
        """Generate image description using Gemini Vision API"""
        if not self.use_gemini or not self.gemini_model:
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
        
        try:
            # Load image
            img = Image.open(image_path)
            
            # Detect article language from context
            context_sample = (context_before + context_after)[:500]
            
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
            
            # Generate description
            response = self.gemini_model.generate_content([full_prompt, img])
            description = response.text.strip()
            
            # Clean up
            image_path.unlink(missing_ok=True)
            
            # Check if AI decided to skip this image
            if description.startswith("SKIP:"):
                # Return a minimal note instead of full description
                self.logger.info(f"Skipped UI element: {image_url}")
                return f"[UI Element - {description[5:].strip()}]"
            
            self.logger.info(f"Generated description for {image_url}: {len(description)} chars")
            return description
            
        except Exception as e:
            self.logger.error(f"Error generating description for {image_url}: {e}")
            print(f"   ⚠️  Gemini API error: {e}")
            image_path.unlink(missing_ok=True)
            return None
    
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
    
    def extract_article_content(self, html_content):
        """Extract main article content from HTML"""
        # Try multiple strategies
        
        # Strategy 1: Elementor widget content (common on this site)
        match = re.search(
            r'<h[12][^>]*>.*?(<h[12][^>]*>.*?</h[12]>.*?)(?=<footer|<div[^>]*class="[^"]*comments|<div[^>]*id="comments)',
            html_content,
            re.DOTALL | re.IGNORECASE
        )
        if match:
            return match.group(1)
        
        # Strategy 2: Article tag
        match = re.search(r'<article[^>]*>(.*?)</article>', html_content, re.DOTALL)
        if match:
            return match.group(1)
        
        # Strategy 3: Main tag
        match = re.search(r'<main[^>]*>(.*?)</main>', html_content, re.DOTALL)
        if match:
            return match.group(1)
        
        raise Exception("Could not find article content")
    
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
    
    def generate_image_description(self, img_data, img_index, total_images):
        """Generate a description for an image (with Gemini if enabled)"""
        
        # Try Gemini first if enabled
        if self.use_gemini:
            print(f"   🤖 Generating AI description for image {img_index + 1}/{total_images}...")
            gemini_desc = self.generate_gemini_description(
                img_data['src'],
                img_data['context_before'],
                img_data['context_after']
            )
            
            if gemini_desc:
                # Format nicely
                desc = f"\n\n**[AI-Generated Image Description {img_index + 1}/{total_images}]**\n\n"
                desc += gemini_desc
                desc += f"\n\n*[Original image: {img_data['src']}]*\n\n"
                
                # Rate limiting
                if img_index < total_images - 1:
                    time.sleep(2)  # 2 second pause between API calls
                
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
    
    def html_to_markdown(self, html_content, images_data):
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
            description = self.generate_image_description(img, i, len(images_data))
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
            # Download
            html_content = self.download_article(url)
            
            # Extract components
            print("📝 Extracting metadata...")
            metadata = self.extract_metadata(html_content)
            
            print("📄 Extracting article content...")
            article_html = self.extract_article_content(html_content)
            
            print("🖼️  Extracting images...")
            images = self.extract_images(article_html)
            print(f"   Found {len(images)} images")
            
            if self.use_gemini and images:
                print(f"🤖 Will generate AI descriptions using Gemini Vision API...")
            
            print("🔄 Converting to Markdown...")
            markdown_content = self.html_to_markdown(article_html, images)
            
            print("💾 Creating Markdown file...")
            output_path = self.create_markdown_file(url, metadata, markdown_content, images)
            
            print(f"✅ Success! Created: {output_path}")
            print(f"   Words: {len(markdown_content.split())}")
            print(f"   Images processed: {len(images)}")
            if self.use_gemini:
                print(f"   AI descriptions: {len(images)}")
            
            return output_path
            
        except Exception as e:
            print(f"❌ Error processing {url}: {str(e)}")
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
    parser.add_argument('-o', '--output', default='.', help='Output directory (default: current directory)')
    parser.add_argument('--gemini', action='store_true', help='Use Gemini Vision API for image descriptions (requires API key)')
    parser.add_argument('--api-key', help='Gemini API key (or set GEMINI_API_KEY environment variable)')
    
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
        gemini_api_key=args.api_key
    )
    
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

