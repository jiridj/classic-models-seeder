"""Salesforce REST API client with retry logic."""

import time
from typing import Optional, Dict, Any, List, Union
import requests

from cmcli.utils.logging import get_logger
from cmcli.utils.retry import retry_with_backoff

logger = get_logger("salesforce.client")


class SalesforceAPIError(Exception):
    """Raised when Salesforce API request fails."""
    pass


class SalesforceRateLimitError(Exception):
    """Raised when Salesforce rate limit is exceeded."""
    pass


class SalesforceClient:
    """Salesforce REST API client with retry logic.
    
    Features:
    - Automatic OAuth token refresh
    - Exponential backoff retry logic
    - Composite API support for batch operations
    - External ID upserts for idempotency
    """
    
    def __init__(self, auth):
        """Initialize Salesforce API client.
        
        Args:
            auth: Salesforce authentication handler (SalesforceAuth or SalesforceWebAuth)
        """
        self.auth = auth
        self.session = requests.Session()
        
        # API version
        self.api_version = auth.config.api_version
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Any] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make an authenticated API request.
        
        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint (relative to instance URL)
            data: Request body data
            params: Query parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            SalesforceAPIError: If request fails
            SalesforceRateLimitError: If rate limit exceeded
        """
        # Build full URL
        instance_url = self.auth.get_instance_url()
        if not endpoint.startswith('/'):
            endpoint = f'/services/data/{self.api_version}/{endpoint}'
        url = f"{instance_url}{endpoint}"
        
        # Get auth headers
        headers = self.auth.get_auth_header()
        headers["Content-Type"] = "application/json"
        
        try:
            logger.debug(f"{method} {url}")
            
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers,
                timeout=30
            )
            
            # Handle 401 (token expired) - refresh and retry once
            if response.status_code == 401:
                logger.info("Token expired, refreshing...")
                self.auth.refresh_token()
                headers = self.auth.get_auth_header()
                headers["Content-Type"] = "application/json"
                
                response = self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=headers,
                    timeout=30
                )
            
            # Handle rate limit
            if response.status_code == 429:
                raise SalesforceRateLimitError(
                    "Salesforce API rate limit exceeded. "
                    "Please wait and try again later, or use a different org."
                )
            
            # Raise for other HTTP errors
            response.raise_for_status()
            
            # Return JSON response or empty dict
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"API request failed: {e}"
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    if isinstance(error_data, list) and len(error_data) > 0:
                        error_msg = f"API error: {error_data[0].get('message', str(e))}"
                    elif isinstance(error_data, dict):
                        error_msg = f"API error: {error_data.get('message', str(e))}"
                except:
                    pass
            logger.error(error_msg)
            raise SalesforceAPIError(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {e}"
            logger.error(error_msg)
            raise SalesforceAPIError(error_msg)
    
    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    def query(self, soql: str) -> List[Dict[str, Any]]:
        """Execute a SOQL query.
        
        Args:
            soql: SOQL query string
            
        Returns:
            List of records
        """
        logger.debug(f"Executing SOQL: {soql}")
        
        response = self._make_request(
            method="GET",
            endpoint="query",
            params={"q": soql}
        )
        
        records = response.get("records", [])
        
        # Handle pagination if needed
        while not response.get("done", True):
            next_records_url = response.get("nextRecordsUrl")
            if next_records_url:
                response = self._make_request(
                    method="GET",
                    endpoint=next_records_url
                )
                records.extend(response.get("records", []))
            else:
                break
        
        logger.debug(f"Query returned {len(records)} records")
        return records
    
    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    def create_record(self, sobject: str, data: Dict[str, Any]) -> str:
        """Create a new record.
        
        Args:
            sobject: Salesforce object type (e.g., 'Account', 'Contact')
            data: Record data
            
        Returns:
            ID of created record
        """
        response = self._make_request(
            method="POST",
            endpoint=f"sobjects/{sobject}",
            data=data
        )
        
        record_id = response.get("id")
        if not record_id:
            raise SalesforceAPIError("Create response missing record ID")
        
        logger.debug(f"Created {sobject} with ID: {record_id}")
        return record_id
    
    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    def update_record(self, sobject: str, record_id: str, data: Dict[str, Any]) -> None:
        """Update an existing record.
        
        Args:
            sobject: Salesforce object type
            record_id: Record ID
            data: Updated data
        """
        self._make_request(
            method="PATCH",
            endpoint=f"sobjects/{sobject}/{record_id}",
            data=data
        )
        
        logger.debug(f"Updated {sobject} {record_id}")
    
    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    def upsert_record(
        self,
        sobject: str,
        external_id_field: str,
        external_id: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Upsert a record using external ID.
        
        Args:
            sobject: Salesforce object type
            external_id_field: External ID field name
            external_id: External ID value
            data: Record data
            
        Returns:
            Dictionary with 'id' and 'created' (bool) keys
        """
        response = self._make_request(
            method="PATCH",
            endpoint=f"sobjects/{sobject}/{external_id_field}/{external_id}",
            data=data
        )
        
        # Response format differs for create vs update
        if response.get("id"):
            # Update - returns ID
            return {"id": response["id"], "created": False}
        elif response.get("success"):
            # Create - returns success and ID
            return {"id": response.get("id"), "created": True}
        else:
            raise SalesforceAPIError(f"Unexpected upsert response: {response}")
    
    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    def delete_record(self, sobject: str, record_id: str) -> None:
        """Delete a record.
        
        Args:
            sobject: Salesforce object type
            record_id: Record ID
        """
        self._make_request(
            method="DELETE",
            endpoint=f"sobjects/{sobject}/{record_id}"
        )
        
        logger.debug(f"Deleted {sobject} {record_id}")
    
    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    def get_record(
        self,
        sobject: str,
        record_id: str,
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get a record by ID.
        
        Args:
            sobject: Salesforce object type
            record_id: Record ID
            fields: Optional list of fields to retrieve
            
        Returns:
            Record data
        """
        params = {}
        if fields:
            params["fields"] = ",".join(fields)
        
        return self._make_request(
            method="GET",
            endpoint=f"sobjects/{sobject}/{record_id}",
            params=params if params else None
        )
    
    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    def describe_object(self, sobject: str) -> Dict[str, Any]:
        """Get object metadata.
        
        Args:
            sobject: Salesforce object type
            
        Returns:
            Object metadata
        """
        return self._make_request(
            method="GET",
            endpoint=f"sobjects/{sobject}/describe"
        )
    
    @retry_with_backoff(max_attempts=3, initial_delay=1.0)
    def composite_request(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute multiple requests in a single API call.
        
        Args:
            requests: List of request specifications
            
        Returns:
            List of responses
        """
        if not requests:
            return []
        
        # Composite API reduces API call count
        # Each composite request counts as 1 call + number of subrequests
        logger.debug(f"Executing composite request with {len(requests)} subrequests")
        
        response = self._make_request(
            method="POST",
            endpoint="composite",
            data={
                "allOrNone": False,
                "compositeRequest": requests
            }
        )
        
        return response.get("compositeResponse", [])
    
    def get_standard_pricebook_id(self) -> str:
        """Get the standard pricebook ID.
        
        Returns:
            Standard pricebook ID
        """
        # Query for standard pricebook
        result = self.query("SELECT Id FROM Pricebook2 WHERE IsStandard = true LIMIT 1")
        if not result:
            raise SalesforceAPIError("Standard pricebook not found")
        return result[0]["Id"]
    
    def create_pricebook_entry(
        self,
        pricebook_id: str,
        product_id: str,
        unit_price: float,
        is_active: bool = True
    ) -> str:
        """Create a pricebook entry.
        
        Args:
            pricebook_id: Pricebook ID
            product_id: Product2 ID
            unit_price: Unit price
            is_active: Whether entry is active
            
        Returns:
            PricebookEntry ID
        """
        data = {
            "Pricebook2Id": pricebook_id,
            "Product2Id": product_id,
            "UnitPrice": unit_price,
            "IsActive": is_active
        }
        return self.create_record("PricebookEntry", data)
    
    def find_pricebook_entry(self, pricebook_id: str, product_id: str) -> Optional[str]:
        """Find a pricebook entry by pricebook and product.
        
        Args:
            pricebook_id: Pricebook ID
            product_id: Product2 ID
            
        Returns:
            PricebookEntry ID or None
        """
        soql = f"""
            SELECT Id
            FROM PricebookEntry
            WHERE Pricebook2Id = '{pricebook_id}'
            AND Product2Id = '{product_id}'
            LIMIT 1
        """
        result = self.query(soql)
        return result[0]["Id"] if result else None
    
    def get_api_usage(self) -> Dict[str, Any]:
        """Get current API usage statistics from Salesforce.
        
        Returns:
            Dictionary with usage information from Salesforce limits API
        """
        try:
            response = self._make_request(
                method="GET",
                endpoint="/services/data/v59.0/limits"
            )
            
            daily_api_requests = response.get("DailyApiRequests", {})
            
            return {
                "calls_made": daily_api_requests.get("Remaining", 0),
                "calls_limit": daily_api_requests.get("Max", 15000),
                "calls_remaining": daily_api_requests.get("Remaining", 0),
                "percentage_used": ((daily_api_requests.get("Max", 15000) - daily_api_requests.get("Remaining", 0)) / daily_api_requests.get("Max", 15000)) * 100 if daily_api_requests.get("Max") else 0
            }
        except Exception as e:
            logger.debug(f"Could not fetch API usage: {e}")
            return {
                "calls_made": 0,
                "calls_limit": 15000,
                "calls_remaining": 15000,
                "percentage_used": 0
            }


# Made with Bob