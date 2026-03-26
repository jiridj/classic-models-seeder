"""Salesforce SOAP API authentication using simple-salesforce."""

import time
from typing import Optional, Dict, Any
import requests
from simple_salesforce import Salesforce, SalesforceLogin

from cmcli.utils.logging import get_logger
from cmcli.config import SalesforceConfig

logger = get_logger("salesforce.auth")


class SalesforceAuthError(Exception):
    """Raised when Salesforce authentication fails."""
    pass


class SalesforceAuth:
    """Handle Salesforce authentication using SOAP API.
    
    Uses simple-salesforce library which handles SOAP authentication.
    """
    
    def __init__(self, config: SalesforceConfig):
        """Initialize with configuration.
        
        Args:
            config: Salesforce configuration
        """
        self.config = config
        self.access_token: Optional[str] = None
        self.instance_url: Optional[str] = None
        self.token_type: str = "Bearer"
        self.token_expires_at: Optional[float] = None
        self.session = requests.Session()
        self._sf: Optional[Salesforce] = None
        
        # Authenticate immediately
        self._authenticate()
    
    def _authenticate(self) -> None:
        """Authenticate using SOAP API via simple-salesforce.
        
        Raises:
            SalesforceAuthError: If authentication fails
        """
        try:
            logger.debug(f"Authenticating with Salesforce using SOAP API")
            logger.debug(f"Username: {self.config.username}")
            
            # Use simple-salesforce to authenticate
            self._sf = Salesforce(
                username=self.config.username,
                password=self.config.password,
                security_token=self.config.security_token,
                domain='login'  # or 'test' for sandbox
            )
            
            # Extract session details
            self.access_token = self._sf.session_id
            self.instance_url = f"https://{self._sf.sf_instance}"
            self.token_type = "Bearer"
            
            # Salesforce sessions typically last 2 hours
            self.token_expires_at = time.time() + (90 * 60)  # 90 minutes
            
            logger.info("Successfully authenticated with Salesforce")
            logger.debug(f"Instance URL: {self.instance_url}")
            
        except Exception as e:
            error_msg = f"Authentication failed: {e}"
            logger.error(error_msg)
            raise SalesforceAuthError(error_msg)
    
    def get_access_token(self) -> str:
        """Get current access token, refreshing if needed.
        
        Returns:
            Valid access token
            
        Raises:
            SalesforceAuthError: If token refresh fails
        """
        # Check if token needs refresh
        if self.token_expires_at and time.time() >= self.token_expires_at:
            logger.info("Access token expired, refreshing...")
            self._authenticate()
        
        if not self.access_token:
            raise SalesforceAuthError("No access token available")
        
        return self.access_token
    
    def get_instance_url(self) -> str:
        """Get Salesforce instance URL.
        
        Returns:
            Instance URL
            
        Raises:
            SalesforceAuthError: If not authenticated
        """
        if not self.instance_url:
            raise SalesforceAuthError("Not authenticated - no instance URL available")
        
        return self.instance_url
    
    def get_auth_header(self) -> Dict[str, str]:
        """Get authorization header for API requests.
        
        Returns:
            Dictionary with Authorization header
        """
        token = self.get_access_token()
        return {"Authorization": f"{self.token_type} {token}"}
    
    def validate_token(self) -> bool:
        """Validate current access token.
        
        Returns:
            True if token is valid, False otherwise
        """
        if not self.access_token or not self.instance_url:
            return False
        
        # Try a simple API call to validate token
        url = f"{self.instance_url}/services/data/{self.config.api_version}"
        headers = self.get_auth_header()
        
        try:
            response = self.session.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def refresh_token(self) -> None:
        """Force token refresh.
        
        Raises:
            SalesforceAuthError: If refresh fails
        """
        logger.info("Forcing token refresh...")
        self._authenticate()


# Made with Bob