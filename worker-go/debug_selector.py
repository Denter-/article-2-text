#!/usr/bin/env python3
"""
Debug script to check what the Go worker selector is extracting
"""
import requests
from bs4 import BeautifulSoup

def test_selector_extraction():
    url = "https://forentrepreneurs.com/saas-metrics-2/"

    print(f"Fetching: {url}")
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Test the primary selector
    primary_selector = ".elementor-widget-theme-post-content"
    primary_elements = soup.select(primary_selector)

    print(f"\n=== Primary Selector: {primary_selector} ===")
    print(f"Found {len(primary_elements)} elements")

    if primary_elements:
        first_element = primary_elements[0]
        content_text = first_element.get_text(strip=True)
        html_content = str(first_element)[:500] + "..." if len(str(first_element)) > 500 else str(first_element)

        print(f"Text length: {len(content_text)} characters")
        print(f"First 200 chars of text: {content_text[:200]}")
        print(f"HTML content: {html_content}")

        # Test exclusions
        exclusions = [
            ".advertisement", ".ad", ".ads", ".sponsored", ".promo", ".promotion",
            ".social-share", ".sharing", ".share-buttons", ".social-media",
            ".related-posts", ".recommended", ".suggestions", ".see-also",
            ".comments", ".comment", ".discussion", ".feedback",
            ".navigation", ".menu", ".breadcrumb", ".pagination",
            ".sidebar", ".widget", ".author-box", ".bio",
            "[class*='ad']", "[class*='ads']", "[class*='advertisement']",
            "[id*='ad']", "[id*='ads']", "[id*='advertisement']",
            "script", "style", "noscript", "iframe", "embed", "object",
            ".widget", "[id*='widget']"
        ]

        print(f"\n=== Testing Exclusions ===")
        excluded_count = 0
        for exclusion in exclusions:
            excluded_elements = first_element.select(exclusion)
            if excluded_elements:
                print(f"Exclusion '{exclusion}' would remove {len(excluded_elements)} elements")
                excluded_count += len(excluded_elements)

        print(f"Total elements that would be excluded: {excluded_count}")

        # Apply exclusions manually to see result
        from copy import deepcopy
        element_copy = deepcopy(first_element)
        for exclusion in exclusions:
            for excluded in element_copy.select(exclusion):
                excluded.decompose()

        final_text = element_copy.get_text(strip=True)
        print(f"Text length after exclusions: {len(final_text)} characters")
        print(f"First 200 chars after exclusions: {final_text[:200]}")

    # Test fallback selector
    fallback_selector = "main"
    fallback_elements = soup.select(fallback_selector)

    print(f"\n=== Fallback Selector: {fallback_selector} ===")
    print(f"Found {len(fallback_elements)} elements")

    if fallback_elements:
        first_element = fallback_elements[0]
        content_text = first_element.get_text(strip=True)
        print(f"Text length: {len(content_text)} characters")
        print(f"First 200 chars of text: {content_text[:200]}")

if __name__ == "__main__":
    test_selector_extraction()