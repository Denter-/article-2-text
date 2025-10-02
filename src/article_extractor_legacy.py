#!/usr/bin/env python3
"""
Article Extractor for ForEntrepreneurs.com
Automatically converts articles to text-only Markdown with image descriptions
"""

import re
import html
import json
import sys
import argparse
from pathlib import Path
from urllib.parse import urlparse
import subprocess

class ArticleExtractor:
    def __init__(self, output_dir="."):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def download_article(self, url):
        """Download article HTML using curl"""
        print(f"📥 Downloading article from {url}...")
        result = subprocess.run(
            ['curl', '-s', url],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise Exception(f"Failed to download article: {result.stderr}")
        return result.stdout
    
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
            
            # Get surrounding text for context (100 chars before and after)
            start = max(0, img_match.start() - 200)
            end = min(len(content), img_match.end() + 200)
            context = content[start:end]
            context_text = re.sub(r'<[^>]+>', ' ', context)
            context_text = html.unescape(context_text).strip()
            
            if src:
                images.append({
                    'src': src.group(1),
                    'alt': alt.group(1) if alt else '',
                    'title': title.group(1) if title else '',
                    'position': img_match.start(),
                    'context': context_text[:400]
                })
        
        return images
    
    def generate_image_description(self, img_data, img_index, total_images):
        """Generate a description for an image based on available context"""
        # Use available metadata
        desc_parts = []
        
        if img_data['alt'] and img_data['alt'].lower() not in ['image', '', 'img']:
            desc_parts.append(f"Alt text: {img_data['alt']}")
        
        if img_data['title'] and img_data['title'].lower() not in ['image', '', 'img']:
            desc_parts.append(f"Title: {img_data['title']}")
        
        # Analyze context for clues
        context = img_data['context'].lower()
        
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
        if desc_parts:
            description = f"\n\n**[{viz_type} {img_index + 1}/{total_images}]**\n\n"
            description += " | ".join(desc_parts)
            description += f"\n\nContext: {img_data['context'][:300]}...\n\n"
        else:
            # Minimal description with context
            description = f"\n\n**[{viz_type} {img_index + 1}/{total_images}]**\n\n"
            description += f"Image in article context: {img_data['context'][:300]}...\n\n"
            description += f"*[Note: For full understanding, refer to the original image at: {img_data['src']}]*\n\n"
        
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
            # Find and replace the image tag
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
        
        header += f"\n**Images:** {len(images)} visualizations converted to text descriptions  \n"
        header += "\n*Note: This is a text-only version. All charts and images have been replaced with contextual descriptions.*\n"
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
            
            print("🔄 Converting to Markdown...")
            markdown_content = self.html_to_markdown(article_html, images)
            
            print("💾 Creating Markdown file...")
            output_path = self.create_markdown_file(url, metadata, markdown_content, images)
            
            print(f"✅ Success! Created: {output_path}")
            print(f"   Words: {len(markdown_content.split())}")
            print(f"   Images processed: {len(images)}")
            
            return output_path
            
        except Exception as e:
            print(f"❌ Error processing {url}: {str(e)}")
            return None


def main():
    parser = argparse.ArgumentParser(
        description='Extract ForEntrepreneurs.com articles to text-only Markdown',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single article
  %(prog)s https://www.forentrepreneurs.com/saas-metrics-2/
  
  # Multiple articles
  %(prog)s https://example.com/article1 https://example.com/article2
  
  # From a file with URLs
  %(prog)s --file urls.txt
  
  # Custom output directory
  %(prog)s --output ./articles https://example.com/article
        """
    )
    
    parser.add_argument('urls', nargs='*', help='Article URLs to process')
    parser.add_argument('-f', '--file', help='File containing URLs (one per line)')
    parser.add_argument('-o', '--output', default='.', help='Output directory (default: current directory)')
    
    args = parser.parse_args()
    
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
    extractor = ArticleExtractor(output_dir=args.output)
    
    print(f"\n🚀 Processing {len(urls)} article(s)...\n")
    
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

