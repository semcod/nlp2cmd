#!/usr/bin/env python3
"""
Test script for NLP2CMD service mode.
"""

import json
import time
import requests
import pytest
from typing import Dict, Any


pytestmark = [pytest.mark.integration, pytest.mark.slow]


def test_service(base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """Test the NLP2CMD service API."""
    
    results = {
        "tests": [],
        "success": True,
        "errors": []
    }
    
    def run_test(name: str, test_func):
        """Run a single test and record results."""
        try:
            result = test_func()
            results["tests"].append({
                "name": name,
                "status": "passed",
                "result": result
            })
            print(f"✅ {name}: PASSED")
        except Exception as e:
            results["tests"].append({
                "name": name,
                "status": "failed",
                "error": str(e)
            })
            results["success"] = False
            results["errors"].append(f"{name}: {e}")
            print(f"❌ {name}: FAILED - {e}")
    
    # Test 1: Health check
    def test_health():
        response = requests.get(f"{base_url}/health")
        response.raise_for_status()
        data = response.json()
        assert data["status"] == "healthy"
        return data
    
    # Test 2: Root endpoint
    def test_root():
        response = requests.get(f"{base_url}/")
        response.raise_for_status()
        data = response.json()
        assert "service" in data
        assert "version" in data
        return data
    
    # Test 3: Simple query
    def test_simple_query():
        payload = {
            "query": "list files in current directory",
            "dsl": "shell"
        }
        response = requests.post(f"{base_url}/query", json=payload)
        response.raise_for_status()
        data = response.json()
        assert data["success"] is True
        assert data["command"] is not None
        assert "ls" in data["command"]
        return data
    
    # Test 4: Query with explanation
    def test_query_with_explanation():
        payload = {
            "query": "find all python files",
            "dsl": "shell",
            "explain": True
        }
        response = requests.post(f"{base_url}/query", json=payload)
        response.raise_for_status()
        data = response.json()
        assert data["success"] is True
        assert data["explanation"] is not None
        return data
    
    # Test 5: Get configuration
    def test_get_config():
        response = requests.get(f"{base_url}/config")
        response.raise_for_status()
        data = response.json()
        assert "host" in data
        assert "port" in data
        return data
    
    # Test 6: Update configuration
    def test_update_config():
        payload = {
            "log_level": "debug"
        }
        response = requests.post(f"{base_url}/config", json=payload)
        response.raise_for_status()
        data = response.json()
        assert data["config"]["log_level"] == "debug"
        return data
    
    # Run all tests
    print("🧪 Testing NLP2CMD Service API")
    print("=" * 40)
    
    run_test("Health Check", test_health)
    run_test("Root Endpoint", test_root)
    run_test("Simple Query", test_simple_query)
    run_test("Query with Explanation", test_query_with_explanation)
    run_test("Get Configuration", test_get_config)
    run_test("Update Configuration", test_update_config)
    
    # Summary
    passed = sum(1 for test in results["tests"] if test["status"] == "passed")
    total = len(results["tests"])
    
    print("=" * 40)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if results["success"]:
        print("🎉 All tests passed!")
    else:
        print("💥 Some tests failed:")
        for error in results["errors"]:
            print(f"  - {error}")
    
    return results


def wait_for_service(base_url: str = "http://localhost:8000", timeout: int = 30):
    """Wait for the service to be ready."""
    print(f"⏳ Waiting for service at {base_url}...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{base_url}/health", timeout=2)
            if response.status_code == 200:
                print("✅ Service is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(1)
        print(".", end="", flush=True)
    
    print(f"\n❌ Service not ready after {timeout} seconds")
    return False


if __name__ == "__main__":
    import sys
    
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    # Wait for service to be ready
    if not wait_for_service(base_url):
        sys.exit(1)
    
    # Run tests
    results = test_service(base_url)
    
    # Exit with appropriate code
    sys.exit(0 if results["success"] else 1)
