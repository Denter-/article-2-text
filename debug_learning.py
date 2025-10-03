#!/usr/bin/env python3
"""
Debug script to test the learning process
"""
import os
import sys
import requests
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_python_worker():
    """Test if Python worker is responding"""
    try:
        response = requests.get("http://localhost:8081/health", timeout=5)
        print(f"Python worker health: {response.status_code}")
        print(f"Response: {response.json()}")
        return True
    except Exception as e:
        print(f"Python worker not responding: {e}")
        return False

def test_learning_endpoint():
    """Test the learning endpoint directly"""
    try:
        data = {
            "job_id": "test-uuid-12345",
            "url": "https://www.forentrepreneurs.com/saas-metrics-2/"
        }
        response = requests.post("http://localhost:8081/learn", json=data, timeout=10)
        print(f"Learning endpoint status: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Learning endpoint error: {e}")
        return False

def test_direct_learning():
    """Test learning directly with site_registry"""
    try:
        from site_registry import SiteRegistry
        
        # Set up environment
        os.environ['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY', '')
        
        registry = SiteRegistry(use_gemini=True)
        
        # Test with a simple HTML
        test_html = """
        <html>
        <body>
        <article>
        <h1>Test Article</h1>
        <p>This is test content.</p>
        </article>
        </body>
        </html>
        """
        
        print("Testing direct learning...")
        result = registry.learn_from_html("https://test.com", test_html, force=True)
        print(f"Learning result: {result}")
        return result[0] if isinstance(result, tuple) else result
        
    except Exception as e:
        print(f"Direct learning error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Debug Learning Process ===")
    
    print("\n1. Testing Python worker health...")
    test_python_worker()
    
    print("\n2. Testing learning endpoint...")
    test_learning_endpoint()
    
    print("\n3. Testing direct learning...")
    test_direct_learning()
    
    print("\n=== Debug Complete ===")


