"""
Simple utility to test API routes
"""
import requests
import sys
import time
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_route(route_path, method="GET", expected_status=200, data=None):
    """Test if a route is accessible"""
    url = f"{BASE_URL}{route_path}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, timeout=5)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, timeout=5)
        else:
            print(f"Unsupported method: {method}")
            return False
            
        actual_status = response.status_code
        is_success = actual_status == expected_status
        
        result = "✅" if is_success else "❌"
        print(f"{result} {method} {route_path} - Expected: {expected_status}, Got: {actual_status}")
        
        # Print response content for debug if failed
        if not is_success:
            print(f"  Response: {response.text[:200]} {'...' if len(response.text) > 200 else ''}")
            
        return is_success
    except Exception as e:
        print(f"❌ {method} {route_path} - Error: {str(e)}")
        return False

def main():
    """Test various API routes"""
    print(f"Testing API routes on {BASE_URL}")
    
    routes = [
        # Basic API
        "/",
        "/api/v1/health",
        "/health",
        
        # Debug routes
        "/api/v1/debug/chat-logs",
        "/api/v1/debug/logs-status",
        
        # Auth routes (these may require authentication)
        #"/api/v1/auth/register",
        
        # Chat routes
        #"/api/v1/chat/characters",
    ]
    
    results = {}
    
    for route in routes:
        results[route] = test_route(route)
        time.sleep(0.5)  # Small delay to avoid overwhelming the server
        
    # Check overall results
    success_count = sum(1 for r in results.values() if r)
    total_count = len(results)
    
    print(f"\nSummary: {success_count}/{total_count} routes accessible")
    
    if success_count < total_count:
        failed_routes = [route for route, success in results.items() if not success]
        print(f"Failed routes: {', '.join(failed_routes)}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
