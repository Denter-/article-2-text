#!/usr/bin/env python3
"""
Debug script to test Google Gemini Vision API for image descriptions
Uses official google-generativeai library
"""

import os
import sys
import json
from pathlib import Path
import time
import urllib.request

# Try to import required libraries
try:
    import google.generativeai as genai
    from PIL import Image
except ImportError as e:
    print("❌ Missing required libraries!")
    print("\nPlease install them:")
    print("  pip install google-generativeai pillow python-dotenv")
    print("\nOr if using venv:")
    print("  source venv/bin/activate")
    print("  pip install google-generativeai pillow python-dotenv")
    sys.exit(1)

# Try to load .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed, using environment variables only")


def load_api_key():
    """Load GEMINI_API_KEY from environment"""
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key or api_key == 'your_api_key_here':
        print("❌ Error: GEMINI_API_KEY not found!")
        print("\nPlease set it:")
        print("1. Create .env file with:")
        print("   GEMINI_API_KEY=your_actual_key_here")
        print("\n2. Or export:")
        print("   export GEMINI_API_KEY='your_actual_key_here'")
        print("\nGet your key from: https://makersuite.google.com/app/apikey")
        sys.exit(1)
    
    return api_key


def download_image(url, output_path):
    """Download image from URL"""
    print(f"📥 Downloading: {url[:60]}...")
    try:
        urllib.request.urlretrieve(url, output_path)
        size = output_path.stat().st_size
        print(f"   ✓ Downloaded: {size:,} bytes")
        
        if size < 100:
            print("   ⚠️  Warning: File seems too small")
            return False
        return True
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False


def generate_description(model, image_path, context_before, context_after):
    """Generate image description using Gemini"""
    
    # Load image
    img = Image.open(image_path)
    
    # Create prompt
    system_context = """You are an expert at analyzing business charts, diagrams, and visualizations for SaaS metrics and business analytics.

Your task is to create detailed, accessible text descriptions that will replace images in a text-only document.

The description MUST:
1. Start by identifying the TYPE (Line Graph, Bar Chart, Table, Diagram, Formula, Dashboard, etc.)
2. Describe what is being measured or visualized
3. Explain the key patterns, trends, or insights visible
4. Include specific data points, axes labels, and important values when present
5. Be comprehensive enough for someone listening via text-to-speech to fully understand

Write in clear, professional language. Do NOT use phrases like "the image shows" - describe directly.
The surrounding article context is provided to help you understand what the visualization illustrates."""

    user_prompt = f"""Analyze this visualization and provide a detailed text description.

ARTICLE CONTEXT BEFORE:
{context_before}

ARTICLE CONTEXT AFTER:
{context_after}

Please provide a comprehensive description of this visualization."""

    full_prompt = system_context + "\n\n" + user_prompt
    
    # Generate content
    print("   🤖 Calling Gemini Vision API...")
    response = model.generate_content([full_prompt, img])
    
    return response.text


def test_image(model, test_case, temp_dir):
    """Test a single image"""
    
    print(f"\n{'='*70}")
    print(f"TEST: {test_case['name']}")
    print('='*70)
    
    # Download image
    image_name = test_case['url'].split('/')[-1].split('?')[0]
    if not any(image_name.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
        image_name += '.png'
    
    image_path = temp_dir / image_name
    
    if not download_image(test_case['url'], image_path):
        return None
    
    try:
        # Generate description
        description = generate_description(
            model,
            image_path,
            test_case['context_before'],
            test_case['context_after']
        )
        
        print(f"\n{'─'*70}")
        print("📝 GENERATED DESCRIPTION:")
        print('─'*70)
        print(description)
        print('─'*70)
        
        return {
            'name': test_case['name'],
            'url': test_case['url'],
            'description': description,
            'image_path': str(image_path),
            'success': True
        }
        
    except Exception as e:
        print(f"\n❌ Error generating description: {e}")
        return {
            'name': test_case['name'],
            'url': test_case['url'],
            'error': str(e),
            'success': False
        }


def main():
    """Main test function"""
    
    print("🧪 Gemini Vision API Test - Official SDK Version")
    print("="*70)
    
    # Load API key
    api_key = load_api_key()
    print("✓ API key loaded")
    
    # Configure Gemini
    genai.configure(api_key=api_key)
    
    # Use Gemini 2.5 Flash (latest fast model with vision)
    model = genai.GenerativeModel('gemini-2.5-flash')
    print("✓ Model initialized: gemini-2.5-flash")
    
    # Create temp directory
    temp_dir = Path('/tmp/gemini_test_images')
    temp_dir.mkdir(exist_ok=True)
    
    # Test cases
    test_cases = [
        {
            "name": "Line Graph: SaaS P&L Trough",
            "url": "https://i0.wp.com/www.forentrepreneurs.com/wp-content/uploads/2012/12/image_thumb28.png?resize=480%2C348",
            "context_before": "SaaS businesses face significant losses in the early years (and often an associated cash flow problem). This is because they have to invest heavily upfront to acquire the customer, but recover the profits from that investment over a long period of time. In many SaaS businesses, this also translates into a cash flow problem, as they may only be able to get the customer to pay them month by month. To illustrate the problem, we built a simple Excel model. In that model, we are spending $6,000 to acquire the customer, and billing them at the rate of $500 per month. Take a look at these two graphs from that model:",
            "context_after": "If we experience a cash flow trough for one customer, then what will happen if we start to do really well and acquire many customers at the same time? The model shows that the P&L/cash flow trough gets deeper if we increase the growth rate for the bookings."
        },
        {
            "name": "Formula/Equation: Negative Churn",
            "url": "https://i0.wp.com/www.forentrepreneurs.com/wp-content/uploads/2012/12/image_thumb3.png?resize=563%2C161",
            "context_before": "The ultimate solution to the churn problem is to get to Negative Churn.",
            "context_after": "There are two ways to get this expansion revenue: 1) Use a pricing scheme that has a variable axis, such as the number of seats used, the number of leads tracked, etc. That way, as your customers expand their usage of your product, they pay you more. 2) Upsell/Cross-sell them to more powerful versions of your product, or additional modules."
        },
        {
            "name": "Data Table: HubSpot Unit Economics",
            "url": "https://i0.wp.com/blogs-images.forbes.com/jjcolao/files/2012/09/HUBSPOT-LTV.png?w=800",
            "context_before": "HubSpot's unit economics were published in an article in Forbes. You can see from the second row in this table how they have dramatically improved their unit economics (LTV:CAC ratio) over the five quarters shown.",
            "context_after": "The big driver for this was lowering the MRR Churn rate from 3.5% to 1.5%. This drove up the lifetime value of the customer considerably. They were also able to drive up their AVG MRR per customer."
        },
        {
            "name": "Multi-Line Graph: Growth Rate Impact",
            "url": "https://i0.wp.com/www.forentrepreneurs.com/wp-content/uploads/2012/12/image_thumb29.png?resize=341%2C435",
            "context_before": "If we experience a cash flow trough for one customer, then what will happen if we start to do really well and acquire many customers at the same time? The model shows that the P&L/cash flow trough gets deeper if we increase the growth rate for the bookings.",
            "context_after": "But there is light at the end of the tunnel, as eventually there is enough profit/cash from the installed base to cover the investment needed for new customers. At that point the business would turn profitable/cash flow positive."
        }
    ]
    
    # Run tests
    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n{'#'*70}")
        print(f"# TEST {i}/{len(test_cases)}")
        print(f"{'#'*70}")
        
        result = test_image(model, test_case, temp_dir)
        if result:
            results.append(result)
        
        # Rate limiting
        if i < len(test_cases):
            print("\n⏳ Waiting 3 seconds (rate limiting)...")
            time.sleep(3)
    
    # Summary
    print(f"\n\n{'='*70}")
    print("📊 TEST SUMMARY")
    print('='*70)
    
    successful = sum(1 for r in results if r.get('success'))
    failed = len(results) - successful
    
    print(f"✅ Successful: {successful}/{len(results)}")
    print(f"❌ Failed: {failed}/{len(results)}")
    
    if successful > 0:
        print("\n✓ Gemini Vision API is working!")
        print("\n📝 Review the descriptions above to verify quality.")
        print("   Check if they:")
        print("   - Correctly identify visualization type")
        print("   - Capture key data and patterns")
        print("   - Provide enough detail for text-only consumption")
        print("   - Understand the business context")
    
    # Save results
    results_file = Path(__file__).parent / 'gemini_test_results.json'
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Results saved to: {results_file.name}")
    
    print(f"\n📁 Downloaded images in: {temp_dir}")
    print("   You can view them to verify description quality")


if __name__ == '__main__':
    main()

