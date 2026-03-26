"""Configuration management for Classic Models CLI."""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv


class HubSpotConfig(BaseModel):
    """HubSpot API configuration."""
    
    access_token: str = Field(..., description="HubSpot API access token")
    account_id: str = Field(..., description="HubSpot account ID")
    
    @classmethod
    def from_env(cls) -> "HubSpotConfig":
        """Load HubSpot configuration from environment variables."""
        access_token = os.getenv("HUBSPOT_ACCESS_TOKEN")
        account_id = os.getenv("HUBSPOT_ACCOUNT_ID")
        
        if not access_token:
            raise ValueError(
                "HUBSPOT_ACCESS_TOKEN not found in environment. "
                "Please set it in your .env file or environment."
            )
        
        if not account_id:
            raise ValueError(
                "HUBSPOT_ACCOUNT_ID not found in environment. "
                "Please set it in your .env file or environment."
            )
        
        return cls(access_token=access_token, account_id=account_id)


class SalesforceConfig(BaseModel):
    """Salesforce SOAP API configuration."""
    
    username: str = Field(..., description="Salesforce username")
    password: str = Field(..., description="Salesforce password")
    security_token: str = Field(..., description="Salesforce security token")
    instance_url: str = Field(..., description="Salesforce instance URL")
    api_version: str = Field(default="v59.0", description="API version")
    
    @classmethod
    def from_env(cls) -> "SalesforceConfig":
        """Load Salesforce configuration from environment variables.
        
        Uses SOAP API authentication (simple username/password/token).
        """
        username = os.getenv("SALESFORCE_USERNAME")
        password = os.getenv("SALESFORCE_PASSWORD")
        security_token = os.getenv("SALESFORCE_SECURITY_TOKEN")
        instance_url = os.getenv("SALESFORCE_INSTANCE_URL")
        api_version = os.getenv("SALESFORCE_API_VERSION", "v59.0")
        
        if not username:
            raise ValueError(
                "SALESFORCE_USERNAME not found in environment. "
                "Please set it in your .env file or environment."
            )
        
        if not password:
            raise ValueError(
                "SALESFORCE_PASSWORD not found in environment. "
                "Please set it in your .env file or environment."
            )
        
        if not security_token:
            raise ValueError(
                "SALESFORCE_SECURITY_TOKEN not found in environment. "
                "Please set it in your .env file or environment."
            )
        
        if not instance_url:
            raise ValueError(
                "SALESFORCE_INSTANCE_URL not found in environment. "
                "Please set it in your .env file or environment."
            )
        
        return cls(
            username=username,
            password=password,
            security_token=security_token,
            instance_url=instance_url,
            api_version=api_version
        )


class ClassicModelsConfig(BaseModel):
    """Classic Models API configuration."""
    
    api_url: str = Field(..., description="Classic Models API base URL")
    username: str = Field(..., description="API username")
    password: str = Field(..., description="API password")
    
    @classmethod
    def from_env(cls) -> "ClassicModelsConfig":
        """Load Classic Models configuration from environment variables."""
        api_url = os.getenv("CLASSIC_MODELS_API_URL")
        username = os.getenv("CLASSIC_MODELS_USERNAME")
        password = os.getenv("CLASSIC_MODELS_PASSWORD")
        
        if not api_url:
            raise ValueError(
                "CLASSIC_MODELS_API_URL not found in environment. "
                "Please set it in your .env file or environment."
            )
        
        if not username:
            raise ValueError(
                "CLASSIC_MODELS_USERNAME not found in environment. "
                "Please set it in your .env file or environment."
            )
        
        if not password:
            raise ValueError(
                "CLASSIC_MODELS_PASSWORD not found in environment. "
                "Please set it in your .env file or environment."
            )
        
        return cls(api_url=api_url, username=username, password=password)


class Config:
    """Main configuration manager."""
    
    def __init__(self, env_file: Optional[Path] = None):
        """Initialize configuration.
        
        Args:
            env_file: Path to .env file. If None, looks for .env in current directory.
        """
        if env_file is None:
            env_file = Path.cwd() / ".env"
        
        if env_file.exists():
            load_dotenv(env_file)
        
        self._hubspot: Optional[HubSpotConfig] = None
        self._salesforce: Optional[SalesforceConfig] = None
        self._classic_models: Optional[ClassicModelsConfig] = None
    
    @property
    def hubspot(self) -> HubSpotConfig:
        """Get HubSpot configuration."""
        if self._hubspot is None:
            self._hubspot = HubSpotConfig.from_env()
        return self._hubspot
    
    @property
    def salesforce(self) -> SalesforceConfig:
        """Get Salesforce configuration."""
        if self._salesforce is None:
            self._salesforce = SalesforceConfig.from_env()
        return self._salesforce
    
    @property
    def classic_models(self) -> ClassicModelsConfig:
        """Get Classic Models configuration."""
        if self._classic_models is None:
            self._classic_models = ClassicModelsConfig.from_env()
        return self._classic_models
    
    @property
    def data_dir(self) -> Path:
        """Get path to data directory."""
        return Path(__file__).parent.parent / "data"
    
    @property
    def json_dir(self) -> Path:
        """Get path to JSON data directory."""
        return self.data_dir / "json"


def get_config(env_file: Optional[Path] = None) -> Config:
    """Get configuration instance.
    
    Args:
        env_file: Path to .env file. If None, looks for .env in current directory.
    
    Returns:
        Config instance
    """
    return Config(env_file=env_file)

# Made with Bob
