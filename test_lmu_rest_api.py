"""
Test LMU REST API to see what vehicle data is available

This script calls various LMU REST API endpoints to discover
what vehicle information is available that might help us get
the actual car make/model (not just team name).

Usage:
    1. Start LMU and join a multiplayer session
    2. Run: python test_lmu_rest_api.py
"""

import json
import requests
import sys


# LMU REST API base URL
BASE_URL = "http://localhost:6397"

# Endpoints to test
ENDPOINTS = [
    "/rest/race/car",
    "/rest/sessions/getAllVehicles",
    "/rest/sessions/getAllAvailableVehicles",
    "/rest/garage/getVehicleCondition",
]


def test_endpoint(endpoint):
    """Test a single endpoint and return the JSON response"""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n{'=' * 80}")
    print(f"Testing: {endpoint}")
    print(f"URL: {url}")
    print('=' * 80)

    try:
        response = requests.get(url, timeout=2)

        if response.status_code == 200:
            print(f"Status: {response.status_code} OK")

            # Try to parse as JSON
            try:
                data = response.json()
                print(f"\nResponse (formatted JSON):")
                print(json.dumps(data, indent=2))
                return data
            except json.JSONDecodeError:
                # Not JSON, show raw text
                print(f"\nResponse (raw text):")
                print(response.text[:1000])  # First 1000 chars
                return response.text
        else:
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return None

    except requests.exceptions.ConnectionError:
        print(f"Connection failed - Is LMU running?")
        return None
    except requests.exceptions.Timeout:
        print(f"Request timed out")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def analyze_vehicle_data(all_data):
    """Analyze collected data to find vehicle identification fields"""
    print("\n" + "=" * 80)
    print("ANALYSIS: Vehicle Identification Fields")
    print("=" * 80)

    print("\nSearching for fields that might contain car make/model...")

    # Keywords to look for
    keywords = ['vehicle', 'car', 'class', 'model', 'make', 'brand', 'name', 'type']

    for endpoint, data in all_data.items():
        if not data:
            continue

        print(f"\n{endpoint}:")
        print("-" * 80)

        # Recursively search for interesting fields
        interesting_fields = find_interesting_fields(data, keywords)

        if interesting_fields:
            for path, value in interesting_fields:
                print(f"  {path}: {value}")
        else:
            print("  (no interesting fields found)")


def find_interesting_fields(obj, keywords, path="", results=None):
    """Recursively find fields matching keywords"""
    if results is None:
        results = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key

            # Check if key matches any keyword
            if any(kw in key.lower() for kw in keywords):
                # Add this field
                if isinstance(value, (str, int, float, bool)):
                    results.append((current_path, value))
                elif isinstance(value, list) and value and isinstance(value[0], (str, int, float)):
                    results.append((current_path, value[:3]))  # First 3 items
                else:
                    results.append((current_path, type(value).__name__))

            # Recurse into nested objects/arrays
            if isinstance(value, (dict, list)):
                find_interesting_fields(value, keywords, current_path, results)

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if i >= 3:  # Only check first 3 items in arrays
                break
            current_path = f"{path}[{i}]"
            if isinstance(item, (dict, list)):
                find_interesting_fields(item, keywords, current_path, results)

    return results


def main():
    print("=" * 80)
    print("LMU REST API Vehicle Data Test")
    print("=" * 80)
    print()
    print("This script will test various LMU REST API endpoints to find")
    print("vehicle identification data (car make/model, not just team name).")
    print()
    print("Prerequisites:")
    print("  1. LMU must be running")
    print("  2. Join a multiplayer session (to have opponent data)")
    print()

    # Test connection
    print("Testing connection to LMU REST API...")
    try:
        response = requests.get(f"{BASE_URL}/rest/sessions", timeout=2)
        print(f"Connected to LMU REST API (status: {response.status_code})")
    except requests.exceptions.ConnectionError:
        print("Cannot connect to LMU REST API at localhost:6397")
        print("  Make sure LMU is running!")
        sys.exit(1)

    # Test all endpoints
    all_data = {}
    for endpoint in ENDPOINTS:
        data = test_endpoint(endpoint)
        all_data[endpoint] = data

    # Analyze results
    analyze_vehicle_data(all_data)

    print("\n" + "=" * 80)
    print("Test Complete!")
    print("=" * 80)
    print()
    print("Next steps:")
    print("  1. Review the output above")
    print("  2. Look for fields that contain car make/model information")
    print("  3. Share this output for analysis")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
