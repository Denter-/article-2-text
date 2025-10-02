#!/usr/bin/env python3
"""
Quick test to verify UI element filtering works
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from article_extractor_with_gemini import ArticleExtractor

def test_ui_filtering():
    """Test that UI elements are properly filtered"""
    
    print("🧪 Testing UI Element Filtering")
    print("="*60)
    
    # Create extractor with Gemini enabled
    extractor = ArticleExtractor(use_gemini=True)
    
    if not extractor.use_gemini:
        print("❌ Gemini not available - check API key")
        return
    
    print("✓ Gemini Vision enabled\n")
    
    # Test image from the definitions page (known to be a button)
    test_image = "https://i0.wp.com/forentrepreneurs.com/wp-content/uploads/2012/12/image35.png?resize=326%2C47"
    
    context_before = """This page is a supplement to the the SaaS Metrics 2.0 blog post. 
    It provides detailed definitions for each of the key metrics used in that post."""
    
    context_after = """Unit Economics is a very powerful way to analyze the long term 
    profitability of a SaaS business."""
    
    print(f"Testing image: {test_image[:60]}...")
    print("\nContext provided:")
    print(f"  Before: {context_before[:80]}...")
    print(f"  After: {context_after[:80]}...")
    print("\n" + "-"*60)
    
    # Generate description
    description = extractor.generate_gemini_description(
        test_image,
        context_before,
        context_after
    )
    
    print("\n📝 RESULT:")
    print("-"*60)
    if description:
        print(description)
        print("-"*60)
        
        if description.startswith("[UI Element"):
            print("\n✅ SUCCESS: UI element was properly filtered!")
            print("   AI recognized this as a button and skipped it.")
        else:
            print("\n⚠️  Note: AI provided full description")
            print("   This might be a content image or needs prompt tuning")
    else:
        print("❌ Error: No description generated")
    
    print("\n" + "="*60)
    print("Test complete!")


if __name__ == '__main__':
    test_ui_filtering()

