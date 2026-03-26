"""Salesforce CRM integration for Classic Models Seeder."""

from cmcli.salesforce.auth import SalesforceAuth
from cmcli.salesforce.client import SalesforceClient
from cmcli.salesforce.seeder import SalesforceSeeder

__all__ = [
    "SalesforceAuth",
    "SalesforceClient", 
    "SalesforceSeeder",
]

# Made with Bob