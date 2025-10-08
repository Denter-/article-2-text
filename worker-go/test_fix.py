#!/usr/bin/env python3
import requests
import json
import time
import sys

def test_extraction():
    """Test extraction directly via API"""
    url = "http://localhost:8080/api/v1/extract"
    payload = {
        "url": "https://forentrepreneurs.com/saas-metrics-2/"
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        print("🚀 Starting extraction test...")
        print(f"URL: {payload['url']}")

        response = requests.post(url, json=payload, headers=headers, timeout=300)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            job_id = result.get('job_id')
            print(f"✅ Job submitted successfully: {job_id}")

            # Poll for results
            results_url = f"http://localhost:8080/api/v1/jobs/{job_id}"
            print(f"⏳ Polling for results...")

            for i in range(60):  # Wait up to 5 minutes
                time.sleep(5)
                results_response = requests.get(results_url)

                if results_response.status_code == 200:
                    job_data = results_response.json()
                    status = job_data.get('status')

                    print(f"Check {i+1}: Status = {status}")

                    if status == 'completed':
                        print("🎉 Extraction completed!")

                        # Check word count
                        word_count = job_data.get('word_count', 0)
                        print(f"Word count: {word_count}")

                        if word_count > 1000:
                            print("✅ SUCCESS: Content extraction appears to be working")
                        else:
                            print("❌ ISSUE: Content extraction still has problems")

                        return job_data
                    elif status == 'failed':
                        error_msg = job_data.get('error_message', 'Unknown error')
                        print(f"❌ Extraction failed: {error_msg}")
                        return None
                else:
                    print(f"❌ Failed to check job status: {results_response.status_code}")

            print("⏰ Timeout: Extraction took too long")
            return None

        else:
            print(f"❌ Failed to submit job: {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error during extraction test: {e}")
        return None

if __name__ == "__main__":
    test_extraction()