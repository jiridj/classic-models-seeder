"""Salesforce OAuth 2.0 Web Server (Authorization Code) flow."""

import time
import webbrowser
import json
import hashlib
import base64
import secrets
from pathlib import Path
from typing import Optional, Dict, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests

from cmcli.utils.logging import get_logger
from cmcli.config import SalesforceConfig

logger = get_logger("salesforce.auth_web")


class SalesforceAuthError(Exception):
    """Raised when Salesforce authentication fails."""
    pass


class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback."""
    
    auth_code: Optional[str] = None
    error: Optional[str] = None
    
    def do_GET(self):
        """Handle GET request with OAuth callback."""
        # Parse query parameters
        query = urlparse(self.path).query
        params = parse_qs(query)
        
        if 'code' in params:
            CallbackHandler.auth_code = params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"""
                <html>
                <body>
                    <h1>Authorization Successful!</h1>
                    <p>You can close this window and return to the terminal.</p>
                    <script>window.close();</script>
                </body>
                </html>
            """)
        elif 'error' in params:
            CallbackHandler.error = params['error'][0]
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(f"""
                <html>
                <body>
                    <h1>Authorization Failed</h1>
                    <p>Error: {params['error'][0]}</p>
                    <p>Description: {params.get('error_description', ['Unknown'])[0]}</p>
                </body>
                </html>
            """.encode())
        
        # Suppress log messages
        def log_message(self, format, *args):
            pass
    
    log_message = lambda self, format, *args: None


class SalesforceWebAuth:
    """Handle Salesforce OAuth 2.0 Web Server flow.
    
    Opens browser for user authorization, then stores refresh token
    for future automated access.
    """
    
    # OAuth endpoints
    AUTHORIZE_ENDPOINT = "/services/oauth2/authorize"
    TOKEN_ENDPOINT = "/services/oauth2/token"
    CALLBACK_PORT = 8080
    CALLBACK_PATH = ""
    
    # Token storage
    TOKEN_FILE = Path.home() / ".cmcli" / "salesforce_tokens.json"
    
    def __init__(self, config: SalesforceConfig):
        """Initialize with OAuth configuration.
        
        Args:
            config: Salesforce OAuth configuration
        """
        self.config = config
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.instance_url: Optional[str] = None
        self.token_type: Optional[str] = None
        self.token_expires_at: Optional[float] = None
        self.session = requests.Session()
        
        # PKCE parameters
        self.code_verifier: Optional[str] = None
        self.code_challenge: Optional[str] = None
        
        # Try to load existing tokens
        if not self._load_tokens():
            # No valid tokens, need to authenticate
            self._authenticate_web_server(use_pkce=False)
    
    def _get_auth_url(self, for_authorization: bool = True) -> str:
        """Determine the correct authentication URL.
        
        Args:
            for_authorization: If True, returns URL for authorization endpoint.
                             If False, returns URL for token endpoint.
        """
        if for_authorization:
            # For authorization, always use login.salesforce.com
            # (or test.salesforce.com for sandboxes)
            if "sandbox" in self.config.instance_url.lower() or "test" in self.config.instance_url.lower():
                return "https://test.salesforce.com"
            return "https://login.salesforce.com"
        else:
            # For token exchange, use instance URL
            return self.config.instance_url.rstrip('/')
    
    def _generate_pkce_params(self) -> None:
        """Generate PKCE code verifier and challenge."""
        # Generate a random code verifier (43-128 characters)
        # Note: Keep padding for Salesforce compatibility
        verifier_bytes = secrets.token_bytes(32)
        self.code_verifier = base64.urlsafe_b64encode(verifier_bytes).decode('utf-8').rstrip('=')
        
        # Generate code challenge (SHA256 hash of verifier)
        challenge_bytes = hashlib.sha256(self.code_verifier.encode('utf-8')).digest()
        self.code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')
        
        logger.debug(f"Generated PKCE verifier length: {len(self.code_verifier)}")
        logger.debug(f"Generated PKCE challenge length: {len(self.code_challenge)}")
    
    def _authenticate_web_server(self, use_pkce: bool = False) -> None:
        """Authenticate using Web Server OAuth flow.
        
        Opens browser for user authorization.
        
        Args:
            use_pkce: Whether to use PKCE (Proof Key for Code Exchange)
        
        Raises:
            SalesforceAuthError: If authentication fails
        """
        auth_url = self._get_auth_url()
        callback_url = f"http://localhost:{self.CALLBACK_PORT}{self.CALLBACK_PATH}"
        
        # Build authorization URL
        from urllib.parse import urlencode
        params = {
            "response_type": "code",
            "client_id": self.config.client_id,
            "redirect_uri": callback_url,
            "scope": "full refresh_token"
        }
        
        # Add PKCE parameters if enabled
        if use_pkce:
            self._generate_pkce_params()
            if self.code_challenge:
                params["code_challenge"] = self.code_challenge
                params["code_challenge_method"] = "S256"
        
        authorize_url = f"{auth_url}{self.AUTHORIZE_ENDPOINT}?{urlencode(params)}"
        
        logger.info("Opening browser for Salesforce authorization...")
        logger.debug(f"Auth URL: {auth_url}")
        logger.debug(f"Params: {params}")
        logger.info(f"If browser doesn't open, visit: {authorize_url}")
        
        # Start local HTTP server for callback
        server = HTTPServer(('localhost', self.CALLBACK_PORT), CallbackHandler)
        
        # Open browser
        webbrowser.open(authorize_url)
        
        # Wait for callback (with timeout)
        logger.info(f"Waiting for authorization callback on port {self.CALLBACK_PORT}...")
        server.timeout = 300  # 5 minutes
        server.handle_request()
        
        # Check for authorization code
        if CallbackHandler.error:
            raise SalesforceAuthError(f"Authorization failed: {CallbackHandler.error}")
        
        if not CallbackHandler.auth_code:
            raise SalesforceAuthError("No authorization code received")
        
        logger.info("Authorization code received, exchanging for access token...")
        
        # Exchange authorization code for access token
        self._exchange_code_for_token(CallbackHandler.auth_code, callback_url)
    
    def _exchange_code_for_token(self, code: str, redirect_uri: str) -> None:
        """Exchange authorization code for access and refresh tokens.
        
        Args:
            code: Authorization code from callback
            redirect_uri: Redirect URI used in authorization
            
        Raises:
            SalesforceAuthError: If token exchange fails
        """
        auth_url = self._get_auth_url(for_authorization=False)
        url = f"{auth_url}{self.TOKEN_ENDPOINT}"
        
        # Build token exchange payload
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.config.client_id,
            "redirect_uri": redirect_uri,
        }
        
        # Add code_verifier if PKCE was used
        if self.code_verifier:
            payload["code_verifier"] = self.code_verifier
        
        # Always add client_secret (Salesforce requires it even with PKCE when "Require secret for Web Server Flow" is enabled)
        payload["client_secret"] = self.config.client_secret
        
        try:
            response = self.session.post(url, data=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")
            self.instance_url = data.get("instance_url")
            self.token_type = data.get("token_type", "Bearer")
            
            if not self.access_token or not self.refresh_token:
                raise SalesforceAuthError("Token response missing required fields")
            
            # Tokens typically expire after 2 hours
            self.token_expires_at = time.time() + (90 * 60)  # 90 minutes
            
            # Save tokens for future use
            self._save_tokens()
            
            logger.info("Successfully authenticated with Salesforce")
            logger.debug(f"Instance URL: {self.instance_url}")
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"Token exchange failed: {e}"
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = f"Token exchange failed: {error_data.get('error_description', str(e))}"
                except ValueError:
                    pass
            logger.error(error_msg)
            raise SalesforceAuthError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during token exchange: {e}"
            logger.error(error_msg)
            raise SalesforceAuthError(error_msg)
    
    def _refresh_access_token(self) -> None:
        """Refresh access token using refresh token.
        
        Raises:
            SalesforceAuthError: If token refresh fails
        """
        if not self.refresh_token:
            raise SalesforceAuthError("No refresh token available")
        
        auth_url = self._get_auth_url()
        url = f"{auth_url}{self.TOKEN_ENDPOINT}"
        
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }
        
        try:
            logger.debug("Refreshing access token...")
            response = self.session.post(url, data=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            self.access_token = data.get("access_token")
            self.instance_url = data.get("instance_url")
            
            if not self.access_token:
                raise SalesforceAuthError("Refresh response missing access token")
            
            self.token_expires_at = time.time() + (90 * 60)
            
            # Save updated tokens
            self._save_tokens()
            
            logger.info("Successfully refreshed access token")
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"Token refresh failed: {e}"
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = f"Token refresh failed: {error_data.get('error_description', str(e))}"
                except ValueError:
                    pass
            logger.error(error_msg)
            # Clear tokens and re-authenticate
            self._clear_tokens()
            raise SalesforceAuthError(f"{error_msg}. Please re-authenticate.")
        except Exception as e:
            error_msg = f"Unexpected error during token refresh: {e}"
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
            self._refresh_access_token()
        
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
            raise SalesforceAuthError("No instance URL available")
        
        return self.instance_url
    
    def validate_token(self) -> bool:
        """Validate current access token.
        
        Returns:
            True if token is valid, False otherwise
        """
        if not self.access_token or not self.instance_url:
            return False
        
        try:
            # Try a simple API call
            url = f"{self.instance_url}/services/data/{self.config.api_version}"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            response = self.session.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def _save_tokens(self) -> None:
        """Save tokens to file for future use."""
        self.TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        tokens = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "instance_url": self.instance_url,
            "token_type": self.token_type,
            "token_expires_at": self.token_expires_at,
            "client_id": self.config.client_id,  # To verify tokens match config
        }
        
        with open(self.TOKEN_FILE, 'w') as f:
            json.dump(tokens, f, indent=2)
        
        # Set restrictive permissions
        self.TOKEN_FILE.chmod(0o600)
        logger.debug(f"Tokens saved to {self.TOKEN_FILE}")
    
    def _load_tokens(self) -> bool:
        """Load tokens from file.
        
        Returns:
            True if tokens loaded successfully, False otherwise
        """
        if not self.TOKEN_FILE.exists():
            return False
        
        try:
            with open(self.TOKEN_FILE, 'r') as f:
                tokens = json.load(f)
            
            # Verify tokens are for the same client
            if tokens.get("client_id") != self.config.client_id:
                logger.debug("Stored tokens are for different client, ignoring")
                return False
            
            self.access_token = tokens.get("access_token")
            self.refresh_token = tokens.get("refresh_token")
            self.instance_url = tokens.get("instance_url")
            self.token_type = tokens.get("token_type")
            self.token_expires_at = tokens.get("token_expires_at")
            
            if not self.refresh_token:
                return False
            
            logger.debug("Loaded tokens from file")
            
            # Validate token
            if not self.validate_token():
                logger.debug("Stored token is invalid, will refresh")
                try:
                    self._refresh_access_token()
                except:
                    return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Failed to load tokens: {e}")
            return False
    
    def _clear_tokens(self) -> None:
        """Clear stored tokens."""
        if self.TOKEN_FILE.exists():
            self.TOKEN_FILE.unlink()
        self.access_token = None
        self.refresh_token = None
        self.instance_url = None
        self.token_expires_at = None

# Made with Bob
