"""
API Client module for Redis Monitor.
Handles API requests to both old database and new Redis-based endpoints.
"""

import requests
import json
from src.config import Config


class APIClient:
    """Client for making API requests to farm metadata endpoints."""

    def __init__(self):
        """Initialize API client with configuration."""
        self.old_endpoint = Config.OLD_API_ENDPOINT
        self.new_endpoint = Config.NEW_API_ENDPOINT
        self.timeout = Config.REQUEST_TIMEOUT

    def _make_request(self, endpoint, farm_id, token, endpoint_type):
        """
        Make HTTP POST request to API endpoint.

        Args:
            endpoint (str): API endpoint URL.
            farm_id (str): Farm ID to query.
            token (str): JWT token for authorization.
            endpoint_type (str): Type of endpoint (old or new) for logging.

        Returns:
            dict: Parsed JSON response or None if request fails.
        """
        try:
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }

            payload = {
                'farmId': farm_id
            }

            if Config.VERBOSE:
                print(f"  → Requesting {endpoint_type} API: {endpoint}")

            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )

            response.raise_for_status()

            data = response.json()

            if Config.VERBOSE:
                print(f"  ✓ {endpoint_type} API response received ({len(json.dumps(data))} bytes)")

            return data

        except requests.exceptions.Timeout:
            print(f"  ✗ {endpoint_type} API request timeout (>{self.timeout}s)")
            return None
        except requests.exceptions.ConnectionError as e:
            print(f"  ✗ {endpoint_type} API connection error: {str(e)}")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"  ✗ {endpoint_type} API HTTP error: {response.status_code} - {str(e)}")
            return None
        except json.JSONDecodeError:
            print(f"  ✗ {endpoint_type} API response is not valid JSON")
            return None
        except Exception as e:
            print(f"  ✗ {endpoint_type} API request failed: {str(e)}")
            return None

    def fetch_old_api(self, farm_id, token):
        """
        Fetch farm metadata from old database-based API.

        Args:
            farm_id (str): Farm ID to query.
            token (str): JWT token for authorization.

        Returns:
            dict: Farm metadata from old API or None if request fails.
        """
        return self._make_request(self.old_endpoint, farm_id, token, "OLD DB")

    def fetch_new_api(self, farm_id, token):
        """
        Fetch farm metadata from new Redis-based API.

        Args:
            farm_id (str): Farm ID to query.
            token (str): JWT token for authorization.

        Returns:
            dict: Farm metadata from new API or None if request fails.
        """
        return self._make_request(self.new_endpoint, farm_id, token, "NEW REDIS")

    def fetch_both(self, farm_id, token):
        """
        Fetch farm metadata from both APIs.

        Args:
            farm_id (str): Farm ID to query.
            token (str): JWT token for authorization.

        Returns:
            tuple: (old_api_response, new_api_response) - each can be dict or None if failed.
        """
        old_data = self.fetch_old_api(farm_id, token)
        new_data = self.fetch_new_api(farm_id, token)
        return old_data, new_data


if __name__ == '__main__':
    # For testing API client
    from src.auth import generate_token

    test_farm_id = '13f9ef67-19b0-4e3d-bec5-6dd15247492c'
    token = generate_token(test_farm_id)

    client = APIClient()
    old_data, new_data = client.fetch_both(test_farm_id, token)

    if old_data:
        print(f"Old API response keys: {list(old_data.keys())}")
    if new_data:
        print(f"New API response keys: {list(new_data.keys())}")
