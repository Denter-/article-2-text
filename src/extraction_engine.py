#!/usr/bin/env python3
"""
Unified Article Extraction Engine
Centralized logic for extracting article content from HTML using site-specific configurations
"""

import re
import logging
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup


class ExtractionEngine:
    """Unified extraction engine used by both SiteRegistry and ArticleExtractor"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
    
    def _clean_html(self, html_content: str) -> str:
        """Clean HTML by removing irrelevant fragments"""
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
    
    def extract_article_html(self, html_content: str, config: Dict[str, Any]) -> Optional[str]:
        """
        Extract article content from HTML using site configuration.
        
        Args:
            html_content: Raw HTML content
            config: Site configuration dictionary
            
        Returns:
            Extracted HTML content or None if extraction fails
        """
        if not html_content or not config:
            return None
        
        # Clean HTML first to remove irrelevant fragments
        html_content = self._clean_html(html_content)
        
        try:
            # Try CSS selector methods first
            content = self._extract_with_selectors(html_content, config)
            if content:
                self.logger.info(f"Extraction successful with CSS selectors")
                return content
            
            # Try content pattern method
            content = self._extract_with_content_pattern(html_content, config)
            if content:
                self.logger.info(f"Extraction successful with content pattern")
                return content
            
            self.logger.warning("All extraction methods failed")
            return None
            
        except Exception as e:
            self.logger.error(f"Extraction error: {e}")
            return None
    
    def _extract_with_selectors(self, html_content: str, config: Dict[str, Any]) -> Optional[str]:
        """Extract content using CSS selectors"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Get article content configuration
        extraction = config.get('extraction', {})
        article_config = extraction.get('article_content', {})
        
        # Try primary selector
        selector = article_config.get('selector')
        if selector:
            element = self._try_selector(soup, selector)
            if element:
                content = self._process_element(element, article_config)
                if content:
                    return content
        
        # Try fallback selector
        fallback = article_config.get('fallback')
        if fallback:
            element = self._try_selector(soup, fallback)
            if element:
                content = self._process_element(element, article_config)
                if content:
                    return content
        
        return None
    
    def _extract_with_content_pattern(self, html_content: str, config: Dict[str, Any]) -> Optional[str]:
        """Extract content using regex patterns"""
        content_pattern = config.get('content_pattern')
        if not content_pattern:
            return None
        
        start_marker = content_pattern.get('start_marker')
        end_marker = content_pattern.get('end_marker')
        
        if not start_marker or not end_marker:
            return None
        
        try:
            # Compile regex safely
            pattern = f"{start_marker}(.*?){end_marker}"
            compiled_pattern = re.compile(pattern, re.DOTALL | re.IGNORECASE)
            
            match = compiled_pattern.search(html_content)
            if match:
                content = match.group(1)
                # Apply basic cleanup
                content = self._apply_basic_cleanup(content)
                if self._is_valid_content(content):
                    return content
            
        except re.error as e:
            self.logger.warning(f"Invalid regex pattern: {e}")
        
        return None
    
    def _try_selector(self, soup: BeautifulSoup, selector: str) -> Optional[BeautifulSoup]:
        """Safely try a CSS selector"""
        try:
            element = soup.select_one(selector)
            if element:
                self.logger.debug(f"Selector '{selector}' found element")
                return element
            else:
                self.logger.debug(f"Selector '{selector}' found no elements")
        except Exception as e:
            self.logger.warning(f"Selector '{selector}' failed: {e}")
        
        return None
    
    def _process_element(self, element: BeautifulSoup, article_config: Dict[str, Any]) -> Optional[str]:
        """Process extracted element with exclusions and cleanup"""
        # Apply truncate_after first (if specified) - removes everything after a boundary selector
        element = self._apply_truncate_after(element, article_config)
        
        # Apply exclusions
        element = self._apply_exclusions(element, article_config)
        
        # Convert to string
        content = str(element)
        
        # Apply cleanup rules
        content = self._apply_cleanup_rules(content, article_config)
        
        # Validate content
        if self._is_valid_content(content):
            return content
        
        return None
    
    def _apply_truncate_after(self, element: BeautifulSoup, article_config: Dict[str, Any]) -> BeautifulSoup:
        """
        Truncate content after a specific selector (removes everything after that element).
        This is useful for removing content that comes after the article ends.
        """
        truncate_after = article_config.get('truncate_after')
        
        if not truncate_after:
            return element
        
        # Make a copy to avoid modifying original
        element_copy = BeautifulSoup(str(element), 'html.parser')
        
        try:
            # Find the boundary element
            boundary = element_copy.select_one(truncate_after)
            if boundary:
                # Remove the boundary element and everything after it
                # Get all siblings after the boundary
                for sibling in list(boundary.find_next_siblings()):
                    sibling.decompose()
                # Remove the boundary itself
                boundary.decompose()
                self.logger.info(f"Truncated after selector: {truncate_after}")
        except Exception as e:
            self.logger.warning(f"Failed to apply truncate_after '{truncate_after}': {e}")
        
        return element_copy
    
    def _apply_exclusions(self, element: BeautifulSoup, article_config: Dict[str, Any]) -> BeautifulSoup:
        """Remove excluded elements from content"""
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
                # Skip invalid selectors
                self.logger.warning(f"Invalid exclude selector '{exclude_selector}': {e}")
                continue
        
        return element_copy
    
    def _apply_cleanup_rules(self, content: str, article_config: Dict[str, Any]) -> str:
        """Apply post-processing cleanup rules"""
        cleanup = article_config.get('cleanup_rules', {})
        
        if not cleanup:
            # Apply default cleanup: truncate at common end markers
            content = self._truncate_at_end_markers(content)
            return content
        
        # Remove specific patterns
        remove_patterns = cleanup.get('remove_patterns', [])
        for pattern in remove_patterns:
            try:
                content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
            except re.error as e:
                self.logger.warning(f"Invalid remove pattern '{pattern}': {e}")
        
        # Stop at repeated links
        if cleanup.get('stop_at_repeated_links', False):
            max_links = cleanup.get('max_consecutive_links', 3)
            content = self._truncate_at_repeated_links(content, max_links)
        else:
            # Apply default truncation if not already done
            content = self._truncate_at_end_markers(content)
        
        return content
    
    def _truncate_at_end_markers(self, content: str) -> str:
        """Truncate content at common end-of-article markers"""
        # Common patterns that indicate end of article content
        end_markers = [
            r'(?i)<[^>]*(?:class|id)[^>]*(?:related|recommended|also.?viewed|more.?from|you.?might|readers.?also)[^>]*>',
            r'(?i)(?:Related Articles?|You [Mm]ight [Aa]lso [Ll]ike|Readers? [Aa]lso [Vv]iewed|More [Ff]rom|Recommended [Ff]or [Yy]ou)',
            r'(?i)View [Mm]ore(?:</[^>]+>){0,3}\s*$',  # "View More" near end
        ]
        
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        
        # Find patterns that indicate > 2 "Read more" links (related articles)
        read_more_count = text.count('Read more')
        if read_more_count > 2:
            # Find where the 3rd "Read more" starts and truncate there
            parts = content.split('Read more')
            if len(parts) > 3:
                # Keep up to 2nd "Read more", truncate rest
                truncated = 'Read more'.join(parts[:3])
                # Find a good breaking point (paragraph end)
                last_p_end = truncated.rfind('</p>')
                if last_p_end > 0:
                    return truncated[:last_p_end + 4]
        
        # Try each end marker pattern
        for pattern in end_markers:
            match = re.search(pattern, content)
            if match:
                # Truncate at this point
                return content[:match.start()]
        
        return content
    
    def _apply_basic_cleanup(self, content: str) -> str:
        """Apply basic cleanup to content pattern results"""
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        content = re.sub(r'  +', ' ', content)
        return content.strip()
    
    def _truncate_at_repeated_links(self, content: str, max_consecutive: int = 3) -> str:
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
    
    def _is_valid_content(self, content: str) -> bool:
        """Check if extracted content is valid (not too short, has substance)"""
        if not content:
            return False
        
        # Remove HTML tags for text length check
        text_content = re.sub(r'<[^>]+>', '', content)
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        # Minimum length check
        if len(text_content) < 500:
            self.logger.debug(f"Content too short: {len(text_content)} characters")
            return False
        
        # Check for substantial content indicators
        soup = BeautifulSoup(content, 'html.parser')
        h1_count = len(soup.find_all('h1'))
        h2_count = len(soup.find_all('h2'))
        p_count = len(soup.find_all('p'))
        
        # Should have some structure
        if h2_count < 2 and p_count < 3:
            self.logger.debug(f"Content lacks structure: H1s={h1_count}, H2s={h2_count}, Ps={p_count}")
            return False
        
        return True


# Convenience function for easy import
def extract_article_html(html_content: str, config: Dict[str, Any], logger=None) -> Optional[str]:
    """Convenience function to extract article content"""
    engine = ExtractionEngine(logger)
    return engine.extract_article_html(html_content, config)
