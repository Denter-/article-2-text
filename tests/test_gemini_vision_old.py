#!/usr/bin/env python3
"""
Debug script to test Google Gemini Vision API for image descriptions
This script downloads test images and sends them to Gemini for description
"""

import os
import sys
import json
import base64
import subprocess
from pathlib import Path
import time

# Try to load API key from various sources
def load_api_key():
    """Load GEMINI_API_KEY from environment or config"""
    # Try environment variable first
    api_key = os.environ.get('GEMINI_API_KEY')
    
    # Try .env file
    if not api_key:
        env_file = Path(__file__).parent / '.env'
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    if line.startswith('GEMINI_API_KEY='):
                        api_key = line.split('=', 1)[1].strip()
                        break
    
    # Try config.json
    if not api_key:
        config_file = Path(__file__).parent / 'config.json'
        if config_file.exists():
            with open(config_file) as f:
                config = json.load(f)
                api_key = config.get('GEMINI_API_KEY')
    
    if not api_key or api_key == 'your_api_key_here':
        print("❌ Error: GEMINI_API_KEY not found!")
        print("\nPlease set it using one of these methods:")
        print("1. Export as environment variable:")
        print("   export GEMINI_API_KEY='your_key_here'")
        print("\n2. Create config.json:")
        print('   {"GEMINI_API_KEY": "your_key_here"}')
        print("\n3. Set in script:")
        print("   Edit this file and set API_KEY variable")
        sys.exit(1)
    
    return api_key


def download_image(url, output_path):
    """Download image from URL"""
    print(f"📥 Downloading image from: {url}")
    result = subprocess.run(
        ['curl', '-s', '-L', url, '-o', output_path],
        capture_output=True
    )
    if result.returncode != 0:
        raise Exception(f"Failed to download image: {result.stderr}")
    return output_path


def encode_image_base64(image_path):
    """Encode image to base64"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def call_gemini_vision(api_key, image_path, context_before, context_after):
    """
    Call Google Gemini Vision API to get image description
    Uses Gemini 1.5 Flash (with vision support)
    """
    
    # Read and encode image
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    
    # Determine mime type
    ext = Path(image_path).suffix.lower()
    mime_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }
    mime_type = mime_types.get(ext, 'image/png')
    
    # Create system prompt
    system_prompt = """You are an expert at analyzing business charts, diagrams, and visualizations. 
Your task is to create detailed, accessible text descriptions of images that will be used in place of the actual images in a text-only document.

The description should:
1. Start by identifying the TYPE of visualization (e.g., "Line Graph", "Bar Chart", "Diagram", "Table", "Dashboard", "Screenshot")
2. Describe what data or concept is being visualized
3. Explain the key insights, patterns, or trends shown
4. Describe important details like axes, labels, data points, colors, or sections
5. Be comprehensive enough that someone listening to the text can fully understand what the image conveys

Write in a clear, professional style. The description will be read aloud or consumed as text-only content.
Do not use phrases like "the image shows" - just describe what's there directly.

Context from the article is provided below to help you understand what the image is illustrating."""

    user_prompt = f"""Please analyze this image and provide a detailed text description.

CONTEXT BEFORE IMAGE:
{context_before[:500]}

CONTEXT AFTER IMAGE:
{context_after[:500]}

Provide a comprehensive description that captures all important information from this visualization."""

    # Prepare API request
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    payload = {
        "contents": [{
            "parts": [
                {"text": system_prompt + "\n\n" + user_prompt},
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": image_data
                    }
                }
            ]
        }],
        "generationConfig": {
            "temperature": 0.4,
            "topK": 32,
            "topP": 1,
            "maxOutputTokens": 2048,
        }
    }
    
    # Make request using curl
    print("🤖 Calling Gemini Vision API...")
    
    # Write payload to temp file
    payload_file = '/tmp/gemini_payload.json'
    with open(payload_file, 'w') as f:
        json.dump(payload, f)
    
    result = subprocess.run([
        'curl', '-s',
        '-H', 'Content-Type: application/json',
        '-d', f'@{payload_file}',
        '-X', 'POST',
        api_url
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        raise Exception(f"API call failed: {result.stderr}")
    
    # Parse response
    try:
        response = json.loads(result.stdout)
        
        if 'error' in response:
            raise Exception(f"API Error: {response['error']}")
        
        # Extract text from response
        if 'candidates' in response and len(response['candidates']) > 0:
            candidate = response['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content']:
                text = candidate['content']['parts'][0].get('text', '')
                return text
        
        raise Exception(f"Unexpected response format: {response}")
        
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse API response: {e}")
        print(f"Response: {result.stdout[:500]}")
        raise


def test_image_description(api_key, image_url, context_before, context_after):
    """Test image description generation"""
    
    print("\n" + "="*60)
    print(f"Testing image: {image_url[:60]}...")
    print("="*60)
    
    # Download image
    temp_dir = Path('/tmp/gemini_test_images')
    temp_dir.mkdir(exist_ok=True)
    
    image_name = image_url.split('/')[-1].split('?')[0]
    if not image_name.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
        image_name += '.png'
    
    image_path = temp_dir / image_name
    
    try:
        download_image(image_url, image_path)
        
        # Check file size
        file_size = image_path.stat().st_size
        print(f"✓ Downloaded: {file_size:,} bytes")
        
        if file_size < 100:
            print("⚠️  Warning: File seems too small, might be an error page")
            return None
        
        # Call Gemini
        description = call_gemini_vision(api_key, image_path, context_before, context_after)
        
        print("\n" + "─"*60)
        print("📝 GENERATED DESCRIPTION:")
        print("─"*60)
        print(description)
        print("─"*60)
        
        return description
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def main():
    """Main test function"""
    
    print("🧪 Gemini Vision API - Image Description Test")
    print("="*60)
    
    # Load API key
    api_key = load_api_key()
    print("✓ API key loaded")
    
    # Test images from the SaaS Metrics article
    test_cases = [
        {
            "name": "Chart 1: SaaS P&L Trough",
            "url": "https://i0.wp.com/www.forentrepreneurs.com/wp-content/uploads/2012/12/image_thumb28.png?resize=480%2C348",
            "context_before": """SaaS businesses face significant losses in the early years (and often an associated cash flow problem). This is because they have to invest heavily upfront to acquire the customer, but recover the profits from that investment over a long period of time. The faster the business decides to grow, the worse the losses become.

In many SaaS businesses, this also translates into a cash flow problem, as they may only be able to get the customer to pay them month by month. To illustrate the problem, we built a simple Excel model. In that model, we are spending $6,000 to acquire the customer, and billing them at the rate of $500 per month. Take a look at these two graphs from that model:""",
            "context_after": """If we experience a cash flow trough for one customer, then what will happen if we start to do really well and acquire many customers at the same time? The model shows that the P&L/cash flow trough gets deeper if we increase the growth rate for the bookings."""
        },
        {
            "name": "Chart 2: Negative Churn Formula",
            "url": "https://i0.wp.com/www.forentrepreneurs.com/wp-content/uploads/2012/12/image_thumb3.png?resize=563%2C161",
            "context_before": """The ultimate solution to the churn problem is to get to Negative Churn.""",
            "context_after": """There are two ways to get this expansion revenue:
1. Use a pricing scheme that has a variable axis, such as the number of seats used, the number of leads tracked, etc.
2. Upsell/Cross-sell them to more powerful versions of your product, or additional modules."""
        },
        {
            "name": "Chart 3: HubSpot Unit Economics",
            "url": "https://i0.wp.com/blogs-images.forbes.com/jjcolao/files/2012/09/HUBSPOT-LTV.png?w=800",
            "context_before": """HubSpot's unit economics were published in an article in Forbes. You can see from the second row in this table how they have dramatically improved their unit economics (LTV:CAC ratio) over the five quarters shown.""",
            "context_after": """The big driver for this was lowering the MRR Churn rate from 3.5% to 1.5%. This drove up the lifetime value of the customer considerably. They were also able to drive up their AVG MRR per customer."""
        }
    ]
    
    # Test each image
    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n{'#'*60}")
        print(f"# TEST {i}/{len(test_cases)}: {test_case['name']}")
        print(f"{'#'*60}")
        
        description = test_image_description(
            api_key,
            test_case['url'],
            test_case['context_before'],
            test_case['context_after']
        )
        
        results.append({
            'name': test_case['name'],
            'url': test_case['url'],
            'description': description,
            'success': description is not None
        })
        
        # Rate limiting - wait between requests
        if i < len(test_cases):
            print("\n⏳ Waiting 2 seconds before next request...")
            time.sleep(2)
    
    # Summary
    print("\n\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    successful = sum(1 for r in results if r['success'])
    print(f"✅ Successful: {successful}/{len(results)}")
    print(f"❌ Failed: {len(results) - successful}/{len(results)}")
    
    if successful > 0:
        print("\n✓ Gemini Vision API is working!")
        print("\n💡 Next steps:")
        print("1. Review the descriptions above")
        print("2. If satisfied, we can integrate into article_extractor.py")
        print("3. Adjust system prompt if needed for better descriptions")
    
    # Save results
    results_file = Path(__file__).parent / 'gemini_test_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to: {results_file}")


if __name__ == '__main__':
    main()

