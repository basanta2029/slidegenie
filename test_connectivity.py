#!/usr/bin/env python3
"""
Test connectivity between frontend and backend
"""

import requests
import sys
import time

def test_backend():
    """Test if backend is accessible"""
    print("🔍 Testing Backend Connection...")
    try:
        # Test backend health endpoint
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running on port 8000")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"⚠️  Backend returned status {response.status_code}")
    except requests.ConnectionError:
        print("❌ Backend is NOT running on port 8000")
        print("   Start it with: cd slidegenie-backend && poetry run uvicorn app.main:app --reload")
    except Exception as e:
        print(f"❌ Backend error: {e}")
    return False

def test_frontend():
    """Test if frontend is accessible"""
    print("\n🔍 Testing Frontend Connection...")
    try:
        # Test frontend home page
        response = requests.get("http://localhost:3000", timeout=5)
        if response.status_code == 200:
            print("✅ Frontend is running on port 3000")
            # Check if it's Next.js
            if 'x-powered-by' in response.headers:
                print(f"   Powered by: {response.headers.get('x-powered-by')}")
            return True
        else:
            print(f"⚠️  Frontend returned status {response.status_code}")
    except requests.ConnectionError:
        print("❌ Frontend is NOT running on port 3000")
        print("   Start it with: cd slidegenie-frontend && npm run dev")
    except Exception as e:
        print(f"❌ Frontend error: {e}")
    return False

def test_api_connectivity():
    """Test if frontend can reach backend API"""
    print("\n🔍 Testing Frontend → Backend API Connection...")
    
    # First check if both are running
    backend_ok = False
    frontend_ok = False
    
    try:
        requests.get("http://localhost:8000/health", timeout=2)
        backend_ok = True
    except:
        pass
        
    try:
        requests.get("http://localhost:3000", timeout=2)
        frontend_ok = True
    except:
        pass
    
    if not backend_ok:
        print("❌ Cannot test API connectivity - Backend is not running")
        return False
    
    if not frontend_ok:
        print("❌ Cannot test API connectivity - Frontend is not running")
        return False
    
    # Test API endpoint
    try:
        response = requests.get("http://localhost:8000/api/v1/health", timeout=5)
        if response.status_code == 200:
            print("✅ API endpoint is accessible")
            return True
        else:
            print(f"⚠️  API returned status {response.status_code}")
    except Exception as e:
        print(f"❌ API connectivity error: {e}")
    
    return False

def main():
    print("SlideGenie Connectivity Test")
    print("=" * 40)
    
    backend_ok = test_backend()
    frontend_ok = test_frontend()
    api_ok = test_api_connectivity()
    
    print("\n📊 Summary:")
    print(f"   Backend:  {'✅ Running' if backend_ok else '❌ Not running'}")
    print(f"   Frontend: {'✅ Running' if frontend_ok else '❌ Not running'}")
    print(f"   API:      {'✅ Connected' if api_ok else '❌ Not connected'}")
    
    if backend_ok and frontend_ok:
        print("\n✅ Both services are running!")
        print("   You can access the app at: http://localhost:3000")
    else:
        print("\n⚠️  Some services are not running.")
        if not backend_ok:
            print("\n📝 To start the backend:")
            print("   cd slidegenie-backend")
            print("   poetry run uvicorn app.main:app --reload")
        if not frontend_ok:
            print("\n📝 To start the frontend:")
            print("   cd slidegenie-frontend")
            print("   npm run dev")

if __name__ == "__main__":
    main()