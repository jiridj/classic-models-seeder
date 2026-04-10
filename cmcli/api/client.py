"""Classic Models API client with JWT authentication and SSL support."""

import os
import requests
import urllib3
from typing import Dict, List, Any, Optional
import logging
import time

from cmcli.config import ClassicModelsConfig
from cmcli.utils.retry import RateLimiter, retry_with_backoff

logger = logging.getLogger(__name__)


class ClassicModelsAPIError(Exception):
    """Base exception for Classic Models API errors."""
    pass


class ClassicModelsAuthError(ClassicModelsAPIError):
    """Authentication error."""
    pass


class ClassicModelsRateLimitError(ClassicModelsAPIError):
    """Rate limit exceeded error."""
    pass


class ClassicModelsServerError(ClassicModelsAPIError):
    """Server error (5xx) that should be retried."""
    pass


class ClassicModelsClient:
    """Classic Models API client with JWT authentication and SSL support."""
    
    def __init__(self, config: ClassicModelsConfig):
        """Initialize Classic Models API client.
        
        Args:
            config: Classic Models configuration with API URL, credentials, and SSL settings
        """
        self.config = config
        self.base_url = config.api_url.rstrip('/')
        self.session = requests.Session()
        
        # Configure SSL verification
        self.session.verify = config.verify_ssl
        if not config.verify_ssl:
            # Suppress SSL warnings when verification is disabled
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logger.warning("SSL verification is disabled. This should only be used in development.")
        
        # JWT tokens
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        
        # Rate limiter: Disabled by default for local API instances
        # Enable if needed by setting rate > 0
        rate_limit = int(os.getenv("CLASSIC_MODELS_RATE_LIMIT", "0"))
        if rate_limit > 0:
            self.rate_limiter = RateLimiter(rate=rate_limit, per=10.0)
            logger.info(f"Rate limiting enabled: {rate_limit} requests per 10 seconds")
        else:
            self.rate_limiter = None
    
    def authenticate(self) -> str:
        """Authenticate with the API and obtain JWT tokens.
        
        Returns:
            Access token
            
        Raises:
            ClassicModelsAuthError: If authentication fails
        """
        url = f"{self.base_url}/api/auth/login/"
        data = {
            "username": self.config.username,
            "password": self.config.password
        }
        
        try:
            response = self.session.post(url, json=data, verify=self.session.verify)
            response.raise_for_status()
            
            tokens = response.json()
            self.access_token = tokens.get("access")
            self.refresh_token = tokens.get("refresh")
            
            if not self.access_token:
                raise ClassicModelsAuthError("No access token received from API")
            
            # Update session headers with access token
            self.session.headers.update({
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            })
            
            logger.info("Successfully authenticated with Classic Models API")
            return self.access_token
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise ClassicModelsAuthError("Invalid credentials")
            raise ClassicModelsAuthError(f"Authentication failed: {e}")
        except requests.exceptions.RequestException as e:
            raise ClassicModelsAuthError(f"Authentication request failed: {e}")
    
    def refresh_access_token(self) -> str:
        """Refresh the access token using the refresh token.
        
        Returns:
            New access token
            
        Raises:
            ClassicModelsAuthError: If refresh fails
        """
        if not self.refresh_token:
            raise ClassicModelsAuthError("No refresh token available")
        
        url = f"{self.base_url}/api/auth/refresh/"
        data = {"refresh": self.refresh_token}
        
        try:
            response = self.session.post(url, json=data, verify=self.session.verify)
            response.raise_for_status()
            
            tokens = response.json()
            self.access_token = tokens.get("access")
            
            if not self.access_token:
                raise ClassicModelsAuthError("No access token received from refresh")
            
            # Update session headers
            self.session.headers.update({
                "Authorization": f"Bearer {self.access_token}"
            })
            
            logger.debug("Successfully refreshed access token")
            return self.access_token
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                # Refresh token expired, need to re-authenticate
                logger.info("Refresh token expired, re-authenticating...")
                return self.authenticate()
            raise ClassicModelsAuthError(f"Token refresh failed: {e}")
        except requests.exceptions.RequestException as e:
            raise ClassicModelsAuthError(f"Token refresh request failed: {e}")
    
    def logout(self):
        """Logout and invalidate the refresh token."""
        if not self.refresh_token:
            return
        
        url = f"{self.base_url}/api/auth/logout/"
        data = {"refresh": self.refresh_token}
        
        try:
            self.session.post(url, json=data, verify=self.session.verify)
            logger.info("Successfully logged out")
        except Exception as e:
            logger.warning(f"Logout failed: {e}")
        finally:
            self.access_token = None
            self.refresh_token = None
            self.session.headers.pop("Authorization", None)
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Any] = None,
        params: Optional[Dict] = None,
        retry_auth: bool = True,
    ) -> Dict[str, Any]:
        """Make an API request with rate limiting and error handling.
        
        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            endpoint: API endpoint path (without base URL)
            data: Request body data
            params: Query parameters
            retry_auth: Whether to retry with token refresh on 401
        
        Returns:
            Response JSON data
        
        Raises:
            ClassicModelsAuthError: If authentication fails
            ClassicModelsRateLimitError: If rate limit is exceeded
            ClassicModelsAPIError: For other API errors
        """
        # Ensure we're authenticated
        if not self.access_token:
            self.authenticate()
        
        # Apply rate limiting if enabled
        if self.rate_limiter:
            self.rate_limiter.wait_if_needed()
        
        # Ensure endpoint starts with /
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                verify=self.session.verify,
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 10))
                logger.warning(f"Rate limit exceeded, waiting {retry_after}s")
                time.sleep(retry_after)
                raise ClassicModelsRateLimitError("Rate limit exceeded")
            
            # Handle authentication errors
            if response.status_code == 401:
                if retry_auth:
                    logger.info("Access token expired, refreshing...")
                    self.refresh_access_token()
                    # Retry the request once with new token
                    return self._make_request(method, endpoint, data, params, retry_auth=False)
                raise ClassicModelsAuthError("Authentication failed")
            
            if response.status_code == 403:
                raise ClassicModelsAuthError("Permission denied")
            
            # Handle server errors (502, 503, 504) - these should be retried
            if response.status_code in (502, 503, 504):
                raise ClassicModelsServerError(f"Server error {response.status_code}: {response.reason}")
            
            # Raise for other HTTP errors
            response.raise_for_status()
            
            # Return JSON response if available
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.HTTPError as e:
            # Don't log 404 as error - it's expected when checking if resources exist
            if e.response.status_code == 404:
                raise ClassicModelsAPIError(f"Resource not found: {endpoint}")
            
            # For other errors, try to get the error message from response
            error_detail = ""
            try:
                if e.response.content:
                    error_json = e.response.json()
                    error_detail = f" - {error_json.get('detail', error_json.get('message', ''))}"
            except:
                pass
            
            logger.error(f"Request failed: {e}{error_detail}")
            raise ClassicModelsAPIError(f"API request failed: {e}{error_detail}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise ClassicModelsAPIError(f"API request failed: {e}")
    
    @retry_with_backoff(
        max_attempts=3,
        exceptions=(ClassicModelsRateLimitError, ClassicModelsServerError, requests.exceptions.RequestException),
    )
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a GET request.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
        
        Returns:
            Response JSON data
        """
        return self._make_request("GET", endpoint, params=params)
    
    @retry_with_backoff(
        max_attempts=3,
        exceptions=(ClassicModelsRateLimitError, ClassicModelsServerError, requests.exceptions.RequestException),
    )
    def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make a POST request.
        
        Args:
            endpoint: API endpoint path
            data: Request body data
        
        Returns:
            Response JSON data
        """
        return self._make_request("POST", endpoint, data=data)
    
    @retry_with_backoff(
        max_attempts=3,
        exceptions=(ClassicModelsRateLimitError, ClassicModelsServerError, requests.exceptions.RequestException),
    )
    def patch(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make a PATCH request.
        
        Args:
            endpoint: API endpoint path
            data: Request body data
        
        Returns:
            Response JSON data
        """
        return self._make_request("PATCH", endpoint, data=data)
    
    @retry_with_backoff(
        max_attempts=3,
        exceptions=(ClassicModelsRateLimitError, ClassicModelsServerError, requests.exceptions.RequestException),
    )
    def put(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make a PUT request.
        
        Args:
            endpoint: API endpoint path
            data: Request body data
        
        Returns:
            Response JSON data
        """
        return self._make_request("PUT", endpoint, data=data)
    
    @retry_with_backoff(
        max_attempts=3,
        exceptions=(ClassicModelsRateLimitError, ClassicModelsServerError, requests.exceptions.RequestException),
    )
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make a DELETE request.
        
        Args:
            endpoint: API endpoint path
        
        Returns:
            Response JSON data
        """
        return self._make_request("DELETE", endpoint)
    
    # Orders API methods
    
    def get_orders(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Get orders with pagination.
        
        Args:
            limit: Maximum number of orders to return
            offset: Number of orders to skip
        
        Returns:
            Response with orders list and pagination info
        """
        params = {"limit": limit, "offset": offset}
        return self.get("/api/v1/orders/", params=params)
    
    def get_order(self, order_number: int) -> Dict[str, Any]:
        """Get a specific order by order number.
        
        Args:
            order_number: Order number
        
        Returns:
            Order data
        """
        return self.get(f"/api/v1/orders/{order_number}/")
    
    def update_order(self, order_number: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an order.
        
        Args:
            order_number: Order number
            data: Order data to update
        
        Returns:
            Updated order data
        """
        return self.patch(f"/api/v1/orders/{order_number}/", data)
    
    # Payments API methods
    
    def get_payments(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Get payments with pagination.
        
        Args:
            limit: Maximum number of payments to return
            offset: Number of payments to skip
        
        Returns:
            Response with payments list and pagination info
        """
        params = {"limit": limit, "offset": offset}
        return self.get("/api/v1/payments/", params=params)
    
    def get_payment(self, customer_number: int, check_number: str) -> Dict[str, Any]:
        """Get a specific payment.
        
        Args:
            customer_number: Customer number
            check_number: Check number
        
        Returns:
            Payment data
        """
        # Payments use composite key: customerNumber + checkNumber
        return self.get(f"/api/v1/payments/{customer_number}/{check_number}/")
    
    def update_payment(self, customer_number: int, check_number: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a payment.
        
        Args:
            customer_number: Customer number
            check_number: Check number
            data: Payment data to update
        
        Returns:
            Updated payment data
        """
        return self.patch(f"/api/v1/payments/{customer_number}/{check_number}/", data)
    
    # Utility methods
    
    def verify_connection(self) -> bool:
        """Verify API connection and authentication.
        
        Returns:
            True if connection is successful
        
        Raises:
            ClassicModelsAPIError: If connection fails
        """
        try:
            self.authenticate()
            # Try to fetch user info
            response = self.get("/api/auth/me/")
            logger.info(f"Connected as user: {response.get('username')}")
            return True
        except Exception as e:
            logger.error(f"Connection verification failed: {e}")
            raise


# Made with Bob