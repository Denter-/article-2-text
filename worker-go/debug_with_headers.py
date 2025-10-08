#!/usr/bin/env python3
"""
Debug script with proper headers to avoid 403
"""
import requests
from bs4 import BeautifulSoup

def test_with_headers():
    url = "https://forentrepreneurs.com/saas-metrics-2/"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    print(f"Fetching: {url}")
    response = requests.get(url, headers=headers)

    print(f"Status code: {response.status_code}")
    print(f"Content length: {len(response.content)}")

    if response.status_code != 200:
        print(f"Failed to fetch: {response.status_code}")
        print(f"Response content: {response.text[:500]}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    print(f"Page title: {soup.title.string if soup.title else 'No title'}")

    # Look for content-related selectors
    content_selectors = [
        ".elementor-widget-theme-post-content",
        ".elementor",
        "main",
        "article",
        "[class*='content']",
        "[class*='post']",
        "[id*='content']",
        "[id*='post']",
        ".entry-content",
        ".post-content",
        ".article-content"
    ]

    print("\n=== Testing Content Selectors ===")
    for selector in content_selectors:
        elements = soup.select(selector)
        print(f"{selector}: {len(elements)} elements")
        if elements:
            first = elements[0]
            text = first.get_text(strip=True)
            print(f"  Text length: {len(text)} chars")
            print(f"  First 100 chars: {text[:100]}...")

    # Look for Elementor structure
    print("\n=== Elementor Structure ===")
    elementor_elements = soup.select("[class*='elementor']")
    print(f"Total Elementor elements: {len(elementor_elements)}")

    # Look for article content in any div with substantial text
    print("\n=== Finding substantial content ===")
    all_divs = soup.find_all('div')
    substantial_divs = []

    for div in all_divs:
        text = div.get_text(strip=True)
        if len(text) > 1000:  # Substantial content
            substantial_divs.append((div, len(text), div.get('class', [])))

    print(f"Found {len(substantial_divs)} divs with >1000 chars of text")

    for i, (div, length, classes) in enumerate(substantial_divs[:3]):  # Top 3
        class_str = ' '.join(classes) if classes else 'no-class'
        print(f"\nDiv {i+1}: {length} chars, classes: {class_str}")
        print(f"First 200 chars: {div.get_text(strip=True)[:200]}...")

if __name__ == "__main__":
    test_with_headers()