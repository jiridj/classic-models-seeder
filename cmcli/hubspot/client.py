"""HubSpot API client with rate limiting and retry logic."""

import requests
from typing import Dict, List, Any, Optional
import logging
import time

from cmcli.config import HubSpotConfig
from cmcli.utils.retry import RateLimiter, retry_with_backoff

logger = logging.getLogger(__name__)


class HubSpotAPIError(Exception):
    """Base exception for HubSpot API errors."""
    pass


class HubSpotAuthError(HubSpotAPIError):
    """Authentication error."""
    pass


class HubSpotRateLimitError(HubSpotAPIError):
    """Rate limit exceeded error."""
    pass


class HubSpotServerError(HubSpotAPIError):
    """Server error (5xx) that should be retried."""
    pass


class HubSpotClient:
    """HubSpot API v3 client with rate limiting and retry logic."""
    
    BASE_URL = "https://api.hubapi.com"
    
    def __init__(self, config: HubSpotConfig):
        """Initialize HubSpot client.
        
        Args:
            config: HubSpot configuration with access token and account ID
        """
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.access_token}",
            "Content-Type": "application/json",
        })
        
        # Rate limiter: 100 requests per 10 seconds for free tier
        self.rate_limiter = RateLimiter(rate=100, per=10.0)
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Any] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make an API request with rate limiting.
        
        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
        
        Returns:
            Response JSON data
        
        Raises:
            HubSpotAuthError: If authentication fails
            HubSpotRateLimitError: If rate limit is exceeded
            HubSpotAPIError: For other API errors
        """
        # Apply rate limiting
        self.rate_limiter.wait_if_needed()
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 10))
                logger.warning(f"Rate limit exceeded, waiting {retry_after}s")
                time.sleep(retry_after)
                raise HubSpotRateLimitError("Rate limit exceeded")
            
            # Handle authentication errors
            if response.status_code == 401:
                raise HubSpotAuthError("Authentication failed. Check your access token.")
            
            if response.status_code == 403:
                raise HubSpotAuthError(
                    "Permission denied. Check your API scopes and permissions."
                )
            
            # Handle server errors (502, 503, 504) - these should be retried
            if response.status_code in (502, 503, 504):
                raise HubSpotServerError(f"Server error {response.status_code}: {response.reason}")
            
            # Raise for other HTTP errors
            response.raise_for_status()
            
            # Return JSON response if available
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.HTTPError as e:
            # Don't log 404 as error - it's expected when checking if resources exist
            if e.response.status_code == 404:
                raise HubSpotAPIError(f"Resource not found: {endpoint}")
            
            # For other errors, try to get the error message from response
            error_detail = ""
            try:
                if e.response.content:
                    error_json = e.response.json()
                    error_detail = f" - {error_json.get('message', '')}"
                    if 'errors' in error_json:
                        error_detail += f" - {error_json['errors']}"
            except:
                pass
            
            logger.error(f"Request failed: {e}{error_detail}")
            raise HubSpotAPIError(f"API request failed: {e}{error_detail}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise HubSpotAPIError(f"API request failed: {e}")
    
    @retry_with_backoff(
        max_attempts=3,
        exceptions=(HubSpotRateLimitError, HubSpotServerError, requests.exceptions.RequestException),
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
        exceptions=(HubSpotRateLimitError, HubSpotServerError, requests.exceptions.RequestException),
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
        exceptions=(HubSpotRateLimitError, HubSpotServerError, requests.exceptions.RequestException),
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
        exceptions=(HubSpotRateLimitError, HubSpotServerError, requests.exceptions.RequestException),
    )
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make a DELETE request.
        
        Args:
            endpoint: API endpoint path
        
        Returns:
            Response JSON data
        """
        return self._make_request("DELETE", endpoint)
    
    # Property management methods
    
    def create_property(
        self,
        object_type: str,
        property_def: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a custom property.
        
        Args:
            object_type: Object type (companies, contacts, deals)
            property_def: Property definition
        
        Returns:
            Created property data
        """
        endpoint = f"/crm/v3/properties/{object_type}"
        return self.post(endpoint, property_def)
    
    def get_property(self, object_type: str, property_name: str) -> Optional[Dict[str, Any]]:
        """Get a property definition.
        
        Args:
            object_type: Object type (companies, contacts, deals, products)
            property_name: Property name
        
        Returns:
            Property data or None if not found
        """
        endpoint = f"/crm/v3/properties/{object_type}/{property_name}"
        try:
            return self.get(endpoint)
        except HubSpotAPIError as e:
            # Don't log 404 errors - property simply doesn't exist yet
            if "404" not in str(e):
                logger.debug(f"Error checking property {object_type}.{property_name}: {e}")
            return None
    
    def list_properties(self, object_type: str) -> List[Dict[str, Any]]:
        """List all properties for an object type.
        
        Args:
            object_type: Object type (companies, contacts, deals)
        
        Returns:
            List of property definitions
        """
        endpoint = f"/crm/v3/properties/{object_type}"
        response = self.get(endpoint)
        return response.get("results", [])
    
    # CRM object methods
    
    def search_objects(
        self,
        object_type: str,
        filter_groups: List[Dict[str, Any]],
        properties: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Search for CRM objects.
        
        Args:
            object_type: Object type (companies, contacts, deals)
            filter_groups: Search filter groups
            properties: Properties to return
            limit: Maximum number of results
        
        Returns:
            List of matching objects
        """
        endpoint = f"/crm/v3/objects/{object_type}/search"
        data = {
            "filterGroups": filter_groups,
            "properties": properties or [],
            "limit": limit,
        }
        response = self.post(endpoint, data)
        return response.get("results", [])
    
    def create_object(
        self,
        object_type: str,
        properties: Dict[str, Any],
        associations: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Create a CRM object.
        
        Args:
            object_type: Object type (companies, contacts, deals)
            properties: Object properties
            associations: Object associations
        
        Returns:
            Created object data
        """
        endpoint = f"/crm/v3/objects/{object_type}"
        data = {"properties": properties}
        if associations:
            data["associations"] = associations
        return self.post(endpoint, data)
    
    def update_object(
        self,
        object_type: str,
        object_id: str,
        properties: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update a CRM object.
        
        Args:
            object_type: Object type (companies, contacts, deals)
            object_id: Object ID
            properties: Properties to update
        
        Returns:
            Updated object data
        """
        endpoint = f"/crm/v3/objects/{object_type}/{object_id}"
        data = {"properties": properties}
        return self.patch(endpoint, data)
    
    def get_object(
        self,
        object_type: str,
        object_id: str,
        properties: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get a CRM object by ID.
        
        Args:
            object_type: Object type (companies, contacts, deals)
            object_id: Object ID
            properties: Properties to return
        
        Returns:
            Object data
        """
        endpoint = f"/crm/v3/objects/{object_type}/{object_id}"
        params = {}
        if properties:
            params["properties"] = ",".join(properties)
        return self.get(endpoint, params=params)
    
    def create_association(
        self,
        from_object_type: str,
        from_object_id: str,
        to_object_type: str,
        to_object_id: str,
        association_type_id: int,
    ) -> Dict[str, Any]:
        """Create an association between two objects.
        
        Args:
            from_object_type: Source object type
            from_object_id: Source object ID
            to_object_type: Target object type
            to_object_id: Target object ID
            association_type_id: Association type ID
        
        Returns:
            Association data
        """
        # Use v4 associations API with PUT method
        endpoint = (
            f"/crm/v4/objects/{from_object_type}/{from_object_id}"
            f"/associations/{to_object_type}/{to_object_id}"
        )
        data = [{
            "associationCategory": "HUBSPOT_DEFINED",
            "associationTypeId": association_type_id
        }]
        return self._make_request("PUT", endpoint, data=data)
    
    # Batch operations
    
    def batch_create(
        self,
        object_type: str,
        objects: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Batch create CRM objects.
        
        Args:
            object_type: Object type (companies, contacts, deals)
            objects: List of objects to create (max 100)
        
        Returns:
            Batch operation results
        """
        endpoint = f"/crm/v3/objects/{object_type}/batch/create"
        data = {"inputs": objects}
        return self.post(endpoint, data)
    
    def batch_update(
        self,
        object_type: str,
        objects: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Batch update CRM objects.
        
        Args:
            object_type: Object type (companies, contacts, deals)
            objects: List of objects to update (max 100)
        
        Returns:
            Batch operation results
        """
        endpoint = f"/crm/v3/objects/{object_type}/batch/update"
        data = {"inputs": objects}
        return self.post(endpoint, data)
    
    # Line item methods
    
    def create_line_item(
        self,
        properties: Dict[str, Any],
        associations: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Create a line item.
        
        Args:
            properties: Line item properties
            associations: Line item associations (to deals, products)
        
        Returns:
            Created line item data
        """
        endpoint = "/crm/v3/objects/line_items"
        data = {"properties": properties}
        if associations:
            data["associations"] = associations
        return self.post(endpoint, data)
    
    def batch_create_line_items(
        self,
        line_items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Batch create line items.
        
        Args:
            line_items: List of line items to create (max 100)
        
        Returns:
            Batch operation results
        """
        endpoint = "/crm/v3/objects/line_items/batch/create"
        data = {"inputs": line_items}
        return self.post(endpoint, data)

# Made with Bob
