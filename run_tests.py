#!/usr/bin/env python3
"""
Simple test runner for KI Kompass API tests
"""

import subprocess
import sys
import os

def run_api_tests():
    """Run the comprehensive API test suite"""
    print("Starting KI Kompass API Test Suite...")
    print("=" * 50)
    
    try:
        # Run the test suite
        result = subprocess.run([
            sys.executable, "test_api.py"
        ], capture_output=True, text=True, timeout=300)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
        
        print(f"\nTest completed with exit code: {result.returncode}")
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Tests timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_api_tests()
    sys.exit(0 if success else 1)