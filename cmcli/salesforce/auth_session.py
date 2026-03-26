"""Salesforce Session ID authentication (simplest method for demos)."""

from typing import Optional, Dict
import requests

from cmcli.utils.logging import get_logger
from cmcli.config import SalesforceConfig

logger = get_logger("salesforce.auth_session")


class SalesforceAuthError(Exception):
    """Raised when Salesforce authentication fails."""
    pass


class SalesforceSessionAuth:
    """Handle Salesforce authentication using Session ID.
    
    This is the simplest authentication method - just use a session ID
    from your browser. Perfect for demos and development.
    
    To get your session ID:
    1. Log into Salesforce in your browser
    2. Open browser developer tools (F12)
    3. Go to Application/Storage → Cookies
    4. Find the 'sid' cookie and copy its value
    5. Add to .env as SALESFORCE_SESSION_ID
    """
    
    def __init__(self, config: SalesforceConfig, session_id: Optional[str] = None):
        """Initialize with session ID.
        
        Args:
            config: Salesforce configuration
            session_id: Salesforce session ID (if not provided, uses config)
        """
        self.config = config
        self.session_id = session_id
        self.instance_url = config.instance_url.rstrip('/')
        self.token_type = "Bearer"
        self.session = requests.Session()
        
        if not self.session_id:
            raise SalesforceAuthError(
                "No session ID provided. Please add SALESFORCE_SESSION_ID to your .env file.\n"
                "To get your session ID:\n"
                "1. Log into Salesforce in your browser\n"
                "2. Open Developer Tools (F12)\n"
                "3. Go to Application → Cookies\n"
                "4. Find 'sid' cookie and copy its value\n"
                "5. Add to .env: SALESFORCE_SESSION_ID=your_session_id"
            )
        
        logger.info("Using Session ID authentication")
        logger.debug(f"Instance URL: {self.instance_url}")
    
    def get_access_token(self) -> str:
        """Get session ID (acts as access token).
        
        Returns:
            Session ID
        """
        return self.session_id
    
    def get_instance_url(self) -> str:
        """Get Salesforce instance URL.
        
        Returns:
            Instance URL
        """
        return self.instance_url
    
    def get_auth_header(self) -> Dict[str, str]:
        """Get authorization header for API requests.
        
        Returns:
            Dictionary with Authorization header
        """
        return {"Authorization": f"Bearer {self.session_id}"}
    
    def validate_token(self) -> bool:
        """Validate current session ID.
        
        Returns:
            True if session is valid, False otherwise
        """
        try:
            # Try a simple API call
            url = f"{self.instance_url}/services/data/{self.config.api_version}"
            headers = self.get_auth_header()
            response = self.session.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return True
            elif response.status_code == 401:
                logger.error("Session ID is invalid or expired. Please get a new session ID.")
                return False
            else:
                logger.error(f"Unexpected response: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error validating session: {e}")
            return False


# Made with Bob