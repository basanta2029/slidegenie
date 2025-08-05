#!/usr/bin/env python3
import time
import requests
import sys

def check_server(url="http://localhost:8000", max_attempts=30):
    """Check if the server is ready."""
    print(f"Checking server at {url}...")
    
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print(f"✓ Server is ready! Response: {response.json()}")
                return True
        except requests.exceptions.ConnectionError:
            print(f"  Attempt {attempt + 1}/{max_attempts}: Connection refused, server starting...")
        except requests.exceptions.Timeout:
            print(f"  Attempt {attempt + 1}/{max_attempts}: Request timed out...")
        except Exception as e:
            print(f"  Attempt {attempt + 1}/{max_attempts}: Error: {e}")
        
        time.sleep(2)
    
    print("✗ Server failed to start within the timeout period")
    return False

if __name__ == "__main__":
    success = check_server()
    sys.exit(0 if success else 1)