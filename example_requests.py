"""
Example API requests for Redis Monitor Flask App.
Run these examples to test the API endpoints.
"""

import requests
import json
from datetime import datetime

# API Base URL - Change this if running on a different host/port
BASE_URL = "http://localhost:5000"

# Colors for console output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def print_header(title):
    """Print a formatted header."""
    print(f"\n{Colors.BLUE}{'=' * 80}")
    print(f"{title}")
    print(f"{'=' * 80}{Colors.RESET}\n")


def print_request(method, endpoint, data=None):
    """Print request details."""
    print(f"{Colors.YELLOW}{method} {endpoint}{Colors.RESET}")
    if data:
        print(f"Body: {json.dumps(data, indent=2)}")
    print()


def print_response(response):
    """Print response details."""
    status_color = Colors.GREEN if response.status_code == 200 else Colors.RED
    print(f"{status_color}Status Code: {response.status_code}{Colors.RESET}")
    try:
        data = response.json()
        print("Response Body:")
        print(json.dumps(data, indent=2))
    except:
        print("Response Body:")
        print(response.text)
    print()


def test_health_check():
    """Test health check endpoint."""
    print_header("1. Health Check Endpoint")
    
    endpoint = f"{BASE_URL}/health"
    print_request("GET", endpoint)
    
    try:
        response = requests.get(endpoint)
        print_response(response)
        return response.status_code == 200
    except Exception as e:
        print(f"{Colors.RED}Error: {str(e)}{Colors.RESET}\n")
        return False


def test_get_docs():
    """Test API documentation endpoint."""
    print_header("2. Get API Documentation")
    
    endpoint = f"{BASE_URL}/api/docs"
    print_request("GET", endpoint)
    
    try:
        response = requests.get(endpoint)
        print_response(response)
        return response.status_code == 200
    except Exception as e:
        print(f"{Colors.RED}Error: {str(e)}{Colors.RESET}\n")
        return False


def test_get_config():
    """Test get configuration endpoint."""
    print_header("3. Get Configuration")
    
    endpoint = f"{BASE_URL}/api/config"
    print_request("GET", endpoint)
    
    try:
        response = requests.get(endpoint)
        print_response(response)
        return response.status_code == 200
    except Exception as e:
        print(f"{Colors.RED}Error: {str(e)}{Colors.RESET}\n")
        return False


def test_monitor_single_farm_get():
    """Test monitor single farm with GET endpoint."""
    print_header("4. Monitor Single Farm (GET)")
    
    farm_id = "13f9ef67-19b0-4e3d-bec5-6dd15247492c"
    endpoint = f"{BASE_URL}/api/monitor/{farm_id}"
    print_request("GET", endpoint)
    
    try:
        response = requests.get(endpoint)
        print_response(response)
        return response.status_code == 200
    except Exception as e:
        print(f"{Colors.RED}Error: {str(e)}{Colors.RESET}\n")
        return False


def test_monitor_single_farm_post():
    """Test monitor single farm with POST endpoint."""
    print_header("5. Monitor Single Farm (POST)")
    
    endpoint = f"{BASE_URL}/api/monitor"
    data = {
        "farmId": "13f9ef67-19b0-4e3d-bec5-6dd15247492c"
    }
    print_request("POST", endpoint, data)
    
    try:
        response = requests.post(endpoint, json=data)
        print_response(response)
        return response.status_code == 200
    except Exception as e:
        print(f"{Colors.RED}Error: {str(e)}{Colors.RESET}\n")
        return False


def test_compare_single_farm():
    """Test compare endpoint with single farm."""
    print_header("6. Compare Multiple Farms (Single Farm)")
    
    endpoint = f"{BASE_URL}/api/compare"
    data = {
        "farmIds": [
            "13f9ef67-19b0-4e3d-bec5-6dd15247492c"
        ],
        "generateReport": False
    }
    print_request("POST", endpoint, data)
    
    try:
        response = requests.post(endpoint, json=data)
        print_response(response)
        return response.status_code == 200
    except Exception as e:
        print(f"{Colors.RED}Error: {str(e)}{Colors.RESET}\n")
        return False


def test_compare_multiple_farms():
    """Test compare endpoint with multiple farms."""
    print_header("7. Compare Multiple Farms (Three Farms)")
    
    endpoint = f"{BASE_URL}/api/compare"
    data = {
        "farmIds": [
            "13f9ef67-19b0-4e3d-bec5-6dd15247492c",
            "farm-id-2",
            "farm-id-3"
        ],
        "generateReport": True
    }
    print_request("POST", endpoint, data)
    
    try:
        response = requests.post(endpoint, json=data)
        print_response(response)
        
        # Print summary if successful
        if response.status_code == 200:
            result = response.json()
            if 'summary' in result:
                print(f"{Colors.GREEN}Summary:{Colors.RESET}")
                print(f"  Total: {result['summary']['total']}")
                print(f"  Identical: {result['summary']['identical']}")
                print(f"  Different: {result['summary']['different']}")
                print(f"  Errors: {result['summary']['errors']}")
                print()
        
        return response.status_code == 200
    except Exception as e:
        print(f"{Colors.RED}Error: {str(e)}{Colors.RESET}\n")
        return False


def test_invalid_request():
    """Test error handling with invalid request."""
    print_header("8. Error Handling (Invalid Request)")
    
    endpoint = f"{BASE_URL}/api/compare"
    data = {
        "farmIds": []  # Empty array - should cause error
    }
    print_request("POST", endpoint, data)
    
    try:
        response = requests.post(endpoint, json=data)
        print_response(response)
        return response.status_code == 400
    except Exception as e:
        print(f"{Colors.RED}Error: {str(e)}{Colors.RESET}\n")
        return False


def test_missing_field():
    """Test error handling with missing required field."""
    print_header("9. Error Handling (Missing Required Field)")
    
    endpoint = f"{BASE_URL}/api/compare"
    data = {}  # Missing farmIds - should cause error
    print_request("POST", endpoint, data)
    
    try:
        response = requests.post(endpoint, json=data)
        print_response(response)
        return response.status_code == 400
    except Exception as e:
        print(f"{Colors.RED}Error: {str(e)}{Colors.RESET}\n")
        return False


def test_not_found():
    """Test 404 error handling."""
    print_header("10. Error Handling (404 Not Found)")
    
    endpoint = f"{BASE_URL}/api/nonexistent"
    print_request("GET", endpoint)
    
    try:
        response = requests.get(endpoint)
        print_response(response)
        return response.status_code == 404
    except Exception as e:
        print(f"{Colors.RED}Error: {str(e)}{Colors.RESET}\n")
        return False


def run_all_tests():
    """Run all test cases."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  REDIS MONITOR - API EXAMPLES AND TESTS".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")
    
    print(f"\n{Colors.YELLOW}Base URL: {BASE_URL}{Colors.RESET}")
    print(f"{Colors.YELLOW}Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}\n")
    
    # Run tests
    tests = [
        ("Health Check", test_health_check),
        ("API Documentation", test_get_docs),
        ("Get Configuration", test_get_config),
        ("Monitor Single Farm (GET)", test_monitor_single_farm_get),
        ("Monitor Single Farm (POST)", test_monitor_single_farm_post),
        ("Compare Single Farm", test_compare_single_farm),
        ("Compare Multiple Farms", test_compare_multiple_farms),
        ("Invalid Request", test_invalid_request),
        ("Missing Required Field", test_missing_field),
        ("404 Not Found", test_not_found),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"{Colors.RED}Test '{test_name}' failed with exception: {str(e)}{Colors.RESET}\n")
            results.append((test_name, False))
    
    # Print summary
    print_header("Test Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{Colors.GREEN}✓ PASSED{Colors.RESET}" if result else f"{Colors.RED}✗ FAILED{Colors.RESET}"
        print(f"{status} - {test_name}")
    
    print(f"\n{Colors.BLUE}Total: {passed}/{total} passed{Colors.RESET}\n")
    
    if passed == total:
        print(f"{Colors.GREEN}All tests passed! API is working correctly.{Colors.RESET}\n")
    else:
        print(f"{Colors.YELLOW}Some tests failed. Check the output above for details.{Colors.RESET}\n")
    
    print(f"{Colors.YELLOW}Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}\n")


if __name__ == '__main__':
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Tests interrupted by user.{Colors.RESET}\n")
