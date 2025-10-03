"""
AI Worker for site learning and complex extractions
Uses existing site_registry.py for LLM-powered config generation
"""
import sys
import os
import json
import logging
import yaml
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, Any

# Add src to path to import site_registry
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from site_registry import SiteRegistry
from app.database import Database

# Import settings from parent
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import settings

logger = logging.getLogger(__name__)


class AIWorker:
    """Worker that handles AI-powered site learning"""
    
    def __init__(self, db: Database):
        self.db = db
        self.site_registry = SiteRegistry(use_gemini=True)
        logger.info("AI Worker initialized with Gemini learning")
    
    def get_domain_from_url(self, url: str) -> str:
        """Extract domain from URL"""
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    
    def process_learning_job(self, job_id: str, url: str) -> Dict[str, Any]:
        """
        Process a job that requires AI learning
        Returns the learned config and extraction result
        """
        logger.info(f"Processing AI learning job {job_id} for {url}")
        
        try:
            # Update status
            self.db.update_job_status(
                job_id, "processing", 10,
                "AI learning: Fetching page..."
            )
            
            # Get domain
            domain = self.get_domain_from_url(url)
            
            # Check if config already exists in DB
            db_config = self.db.get_site_config(domain)
            
            if db_config:
                logger.info(f"Found existing config for {domain} in database")
                # Use existing config
                config_yaml = db_config['config_yaml']
                config = yaml.safe_load(config_yaml) if config_yaml else None
            else:
                # Need to learn
                self.db.update_job_status(
                    job_id, "processing", 30,
                    "AI learning: Analyzing page structure..."
                )
                
                logger.info(f"No config found for {domain}, starting AI learning")
                
                # Fetch page (with browser for JS sites)
                import requests
                try:
                    response = requests.get(url, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }, timeout=30)
                    html_content = response.text
                except Exception as e:
                    # If regular fetch fails, try with browser
                    logger.info(f"Regular fetch failed, trying with browser: {e}")
                    html_content = self.site_registry.fetch_with_browser(url)
                
                if not html_content:
                    raise Exception("Failed to fetch page")
                
                # Learn config using Gemini
                self.db.update_job_status(
                    job_id, "processing", 50,
                    "AI learning: Generating extraction rules..."
                )
                
                success, config, error = self.site_registry.learn_from_html(url, html_content)
                
                if not success or not config:
                    raise Exception(f"Failed to learn site structure: {error}")
                
                # Save to file system (for compatibility)
                self.site_registry.save_config(domain, config)
                
                # Save to database
                config_yaml = yaml.dump(config, default_flow_style=False)
                job = self.db.get_job(job_id)
                requires_browser = config.get('requires_browser', False)
                
                self.db.save_site_config(
                    domain, config_yaml, requires_browser, 
                    job['user_id']
                )
                
                logger.info(f"Learned and saved config for {domain}")
            
            # Extract article
            self.db.update_job_status(
                job_id, "processing", 70,
                "Extracting article content..."
            )
            
            # Fetch fresh content for extraction
            import requests
            try:
                response = requests.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }, timeout=30)
                html_content = response.text
            except:
                html_content = self.site_registry.fetch_with_browser(url)
            
            # Extract with config
            result = self.site_registry.extract_with_config(html_content, config)
            
            if not result or not result.get('content'):
                raise Exception("Failed to extract article content")
            
            # Save markdown
            self.db.update_job_status(
                job_id, "processing", 90,
                "Saving results..."
            )
            
            # Generate filename from title
            title = result.get('title', 'untitled')
            safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' 
                               for c in title)
            safe_title = safe_title.replace(' ', '_')[:100]
            
            storage_path = Path(settings.storage_path)
            storage_path.mkdir(parents=True, exist_ok=True)
            
            filename = f"{safe_title}.md"
            filepath = storage_path / filename
            
            # Generate markdown
            markdown = self._generate_markdown(result)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown)
            
            # Update job with results
            self.db.update_job_result(
                job_id, str(filepath),
                title=result.get('title'),
                author=result.get('author'),
                word_count=result.get('word_count', 0),
                image_count=len(result.get('images', []))
            )
            
            # Mark complete
            self.db.update_job_status(
                job_id, "completed", 100,
                "Article extracted successfully"
            )
            
            logger.info(f"Job {job_id} completed successfully")
            
            return {
                'success': True,
                'config': config,
                'result': result,
                'filepath': str(filepath)
            }
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            self.db.update_job_status(
                job_id, "failed", error=str(e)
            )
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_markdown(self, result: Dict[str, Any]) -> str:
        """Generate markdown from extraction result"""
        lines = []
        
        # Title
        if result.get('title'):
            lines.append(f"# {result['title']}\n")
        
        # Metadata
        if result.get('author'):
            lines.append(f"**Author:** {result['author']}\n")
        
        if result.get('published_date'):
            lines.append(f"**Published:** {result['published_date']}\n")
        
        lines.append("---\n")
        
        # Content
        lines.append(result.get('content', ''))
        
        # Images
        images = result.get('images', [])
        if images:
            lines.append("\n\n## Images\n")
            for img in images:
                src = img.get('src', '')
                alt = img.get('alt', 'Image')
                desc = img.get('description', '')
                lines.append(f"\n![{alt}]({src})\n")
                if desc:
                    lines.append(f"*{desc}*\n")
        
        return '\n'.join(lines)


# For missing import
import yaml

