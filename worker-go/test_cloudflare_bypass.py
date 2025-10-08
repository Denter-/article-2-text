#!/usr/bin/env python3
"""
Test if our Cloudflare bypass headers work
"""
import requests

def test_cloudflare_bypass():
    url = "https://forentrepreneurs.com/saas-metrics-2/"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    print(f"Testing Cloudflare bypass for: {url}")
    response = requests.get(url, headers=headers)

    print(f"Status code: {response.status_code}")
    print(f"Content length: {len(response.content)}")

    if response.status_code == 200:
        # Look for Elementor content
        if 'elementor-widget-theme-post-content' in response.text:
            print("✅ Found .elementor-widget-theme-post-content selector")
        else:
            print("❌ .elementor-widget-theme-post-content selector not found")

        # Look for other content selectors
        selectors_to_check = [
            'elementor',
            'main',
            'article',
            'entry-content',
            'post-content'
        ]

        for selector in selectors_to_check:
            if selector in response.text.lower():
                print(f"✅ Found '{selector}' in HTML")
            else:
                print(f"❌ '{selector}' not found in HTML")

        # Check for actual article content
        if 'saas metrics' in response.text.lower():
            print("✅ Found article content (saas metrics)")
        else:
            print("❌ Article content not found")

        # Save a snippet to see what we got
        print(f"\nFirst 500 characters of HTML:")
        print(response.text[:500])
        print(f"\nLast 500 characters of HTML:")
        print(response.text[-500:])

    else:
        print(f"❌ Failed with status: {response.status_code}")
        print(f"Response: {response.text[:200]}")

if __name__ == "__main__":
    test_cloudflare_bypass()