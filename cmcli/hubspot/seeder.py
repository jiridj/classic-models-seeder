"""HubSpot seeding orchestration."""

from typing import Dict, List, Any, Optional, Set
import logging
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.console import Console

from cmcli.hubspot.client import HubSpotClient, HubSpotAPIError
from cmcli.hubspot.transformers import HubSpotTransformer
from cmcli.hubspot.properties import get_properties_for_object
from cmcli.data.loader import DataLoader

logger = logging.getLogger(__name__)
console = Console()


class HubSpotSeeder:
    """Orchestrate seeding of HubSpot CRM with Classic Models data."""
    
    # HubSpot association type IDs
    COMPANY_TO_CONTACT = 2  # Company to Contact
    CONTACT_TO_COMPANY = 1  # Contact to Company
    COMPANY_TO_DEAL = 6     # Company to Deal
    DEAL_TO_COMPANY = 5     # Deal to Company
    CONTACT_TO_DEAL = 4     # Contact to Deal
    DEAL_TO_CONTACT = 3     # Deal to Contact
    
    def __init__(self, client: HubSpotClient, data_loader: DataLoader):
        """Initialize seeder.
        
        Args:
            client: HubSpot API client
            data_loader: Data loader for Classic Models data
        """
        self.client = client
        self.data_loader = data_loader
        self.transformer = HubSpotTransformer()
        
        # Track created objects for associations
        self.company_ids: Dict[int, str] = {}  # customer_number -> company_id
        self.contact_ids: Dict[int, str] = {}  # customer_number -> contact_id
        self.deal_ids: Dict[int, str] = {}     # order_number -> deal_id
    
    def ensure_properties_exist(self, object_types: List[str]) -> None:
        """Ensure custom properties exist for object types.
        
        Args:
            object_types: List of object types to check ('companies', 'contacts', 'deals')
        """
        console.print("\n[bold]Checking custom properties...[/bold]")
        
        for object_type in object_types:
            properties = get_properties_for_object(object_type)
            
            for prop_def in properties:
                prop_name = prop_def["name"]
                
                # Check if property exists
                existing = self.client.get_property(object_type, prop_name)
                
                if existing:
                    logger.debug(f"Property {object_type}.{prop_name} already exists")
                else:
                    logger.info(f"Creating property {object_type}.{prop_name}")
                    try:
                        self.client.create_property(object_type, prop_def)
                        console.print(f"  ✓ Created {object_type}.{prop_name}")
                    except HubSpotAPIError as e:
                        logger.error(f"Failed to create property {prop_name}: {e}")
                        raise
        
        console.print("[green]✓ All custom properties ready[/green]")
    
    def seed_companies(self, customers: Optional[List[Dict[str, Any]]] = None) -> int:
        """Seed companies from customers.
        
        Args:
            customers: Optional list of customer records. If None, loads from data files.
        
        Returns:
            Number of companies created/updated
        """
        if customers is None:
            customers = self.data_loader.load_customers()
        
        console.print(f"\n[bold]Seeding {len(customers)} companies...[/bold]")
        
        created = 0
        updated = 0
        skipped = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Processing companies...", total=len(customers))
            
            for customer in customers:
                customer_number = customer["customerNumber"]
                
                # Transform to HubSpot format
                properties = self.transformer.transform_customer_to_company(customer)
                
                # Check if company already exists
                existing = self._find_company_by_erp_id(str(customer_number))
                
                try:
                    if existing:
                        # Update existing company
                        company_id = existing["id"]
                        self.client.update_object("companies", company_id, properties)
                        self.company_ids[customer_number] = company_id
                        updated += 1
                        logger.debug(f"Updated company {customer_number}")
                    else:
                        # Create new company
                        result = self.client.create_object("companies", properties)
                        company_id = result["id"]
                        self.company_ids[customer_number] = company_id
                        created += 1
                        logger.debug(f"Created company {customer_number}")
                except HubSpotAPIError as e:
                    logger.warning(f"Failed to upsert company {customer_number}: {e}")
                    skipped += 1
                
                progress.update(task, advance=1)
        
        console.print(f"[green]✓ Companies: {created} created, {updated} updated, {skipped} skipped[/green]")
        return created + updated
    
    def seed_contacts(self, customers: Optional[List[Dict[str, Any]]] = None) -> int:
        """Seed contacts from customers.
        
        Args:
            customers: Optional list of customer records. If None, loads from data files.
        
        Returns:
            Number of contacts created/updated
        """
        if customers is None:
            customers = self.data_loader.load_customers()
        
        console.print(f"\n[bold]Seeding {len(customers)} contacts...[/bold]")
        
        created = 0
        updated = 0
        skipped = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Processing contacts...", total=len(customers))
            
            for customer in customers:
                customer_number = customer["customerNumber"]
                
                # Transform to HubSpot format
                properties = self.transformer.transform_customer_to_contact(customer)
                
                # Check if contact already exists
                existing = self._find_contact_by_erp_id(str(customer_number))
                
                try:
                    if existing:
                        # Update existing contact
                        contact_id = existing["id"]
                        self.client.update_object("contacts", contact_id, properties)
                        self.contact_ids[customer_number] = contact_id
                        updated += 1
                        logger.debug(f"Updated contact {customer_number}")
                    else:
                        # Create new contact
                        result = self.client.create_object("contacts", properties)
                        contact_id = result["id"]
                        self.contact_ids[customer_number] = contact_id
                        created += 1
                        logger.debug(f"Created contact {customer_number}")
                        
                        # Associate with company if it exists
                        if customer_number in self.company_ids:
                            company_id = self.company_ids[customer_number]
                            try:
                                self.client.create_association(
                                    "contacts", contact_id,
                                    "companies", company_id,
                                    self.CONTACT_TO_COMPANY
                                )
                            except HubSpotAPIError as e:
                                # Silently ignore 405 errors (association already exists)
                                if "405" not in str(e):
                                    logger.warning(f"Failed to associate contact with company: {e}")
                
                except HubSpotAPIError as e:
                    logger.warning(f"Failed to upsert contact {customer_number}: {e}")
                    skipped += 1
                
                progress.update(task, advance=1)
        
        console.print(f"[green]✓ Contacts: {created} created, {updated} updated, {skipped} skipped[/green]")
        return created + updated
    
    def seed_deals(
        self,
        orders: Optional[List[Dict[str, Any]]] = None,
        order_details: Optional[List[Dict[str, Any]]] = None,
        payments: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        """Seed deals from orders.
        
        Args:
            orders: Optional list of order records. If None, loads from data files.
            order_details: Optional list of order detail records. If None, loads from data files.
            payments: Optional list of payment records. If None, loads from data files.
        
        Returns:
            Number of deals created/updated
        """
        if orders is None:
            orders = self.data_loader.load_orders()
        if order_details is None:
            order_details = self.data_loader.load_order_details()
        if payments is None:
            payments = self.data_loader.load_payments()
        
        console.print(f"\n[bold]Seeding {len(orders)} deals...[/bold]")
        
        created = 0
        updated = 0
        skipped = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Processing deals...", total=len(orders))
            
            for order in orders:
                order_number = order["orderNumber"]
                customer_number = order["customerNumber"]
                
                # Transform to HubSpot format
                properties = self.transformer.transform_order_to_deal(
                    order, order_details, payments
                )
                
                # Check if deal already exists
                existing = self._find_deal_by_erp_id(str(order_number))
                
                try:
                    if existing:
                        # Update existing deal
                        deal_id = existing["id"]
                        self.client.update_object("deals", deal_id, properties)
                        self.deal_ids[order_number] = deal_id
                        updated += 1
                        logger.debug(f"Updated deal {order_number}")
                    else:
                        # Create new deal
                        result = self.client.create_object("deals", properties)
                        deal_id = result["id"]
                        self.deal_ids[order_number] = deal_id
                        created += 1
                        logger.debug(f"Created deal {order_number}")
                        
                        # Associate with company and contact if they exist
                        if customer_number in self.company_ids:
                            company_id = self.company_ids[customer_number]
                            try:
                                self.client.create_association(
                                    "deals", deal_id,
                                    "companies", company_id,
                                    self.DEAL_TO_COMPANY
                                )
                            except HubSpotAPIError as e:
                                # Silently ignore 405 errors (association already exists)
                                if "405" not in str(e):
                                    logger.warning(f"Failed to associate deal with company: {e}")
                        
                        if customer_number in self.contact_ids:
                            contact_id = self.contact_ids[customer_number]
                            try:
                                self.client.create_association(
                                    "deals", deal_id,
                                    "contacts", contact_id,
                                    self.DEAL_TO_CONTACT
                                )
                            except HubSpotAPIError as e:
                                # Silently ignore 405 errors (association already exists)
                                if "405" not in str(e):
                                    logger.warning(f"Failed to associate deal with contact: {e}")
                
                except HubSpotAPIError as e:
                    logger.warning(f"Failed to upsert deal {order_number}: {e}")
                    skipped += 1
                
                progress.update(task, advance=1)
        
        console.print(f"[green]✓ Deals: {created} created, {updated} updated, {skipped} skipped[/green]")
        return created + updated
    
    def _find_company_by_erp_id(self, erp_customer_number: str) -> Optional[Dict[str, Any]]:
        """Find a company by ERP customer number.
        
        Args:
            erp_customer_number: ERP customer number
        
        Returns:
            Company object or None if not found
        """
        try:
            results = self.client.search_objects(
                "companies",
                filter_groups=[{
                    "filters": [{
                        "propertyName": "erp_customer_number",
                        "operator": "EQ",
                        "value": erp_customer_number,
                    }]
                }],
                limit=1,
            )
            return results[0] if results else None
        except HubSpotAPIError:
            return None
    
    def _find_contact_by_erp_id(self, erp_customer_number: str) -> Optional[Dict[str, Any]]:
        """Find a contact by ERP customer number.
        
        Args:
            erp_customer_number: ERP customer number
        
        Returns:
            Contact object or None if not found
        """
        try:
            results = self.client.search_objects(
                "contacts",
                filter_groups=[{
                    "filters": [{
                        "propertyName": "erp_customer_number",
                        "operator": "EQ",
                        "value": erp_customer_number,
                    }]
                }],
                limit=1,
            )
            return results[0] if results else None
        except HubSpotAPIError:
            return None
    
    def _find_deal_by_erp_id(self, erp_order_number: str) -> Optional[Dict[str, Any]]:
        """Find a deal by ERP order number.
        
        Args:
            erp_order_number: ERP order number
        
        Returns:
            Deal object or None if not found
        """
        try:
            results = self.client.search_objects(
                "deals",
                filter_groups=[{
                    "filters": [{
                        "propertyName": "erp_order_number",
                        "operator": "EQ",
                        "value": erp_order_number,
                    }]
                }],
                limit=1,
            )
            return results[0] if results else None
        except HubSpotAPIError:
            return None
    
    def seed_all(self) -> Dict[str, int]:
        """Seed all data (companies, contacts, deals).
        
        Returns:
            Dictionary with counts for each object type
        """
        # Load all data once
        customers = self.data_loader.load_customers()
        orders = self.data_loader.load_orders()
        order_details = self.data_loader.load_order_details()
        payments = self.data_loader.load_payments()
        
        # Ensure properties exist
        self.ensure_properties_exist(["companies", "contacts", "deals"])
        
        # Seed in order: companies -> contacts -> deals
        companies_count = self.seed_companies(customers)
        contacts_count = self.seed_contacts(customers)
        deals_count = self.seed_deals(orders, order_details, payments)
        
        return {
            "companies": companies_count,
            "contacts": contacts_count,
            "deals": deals_count,
        }

# Made with Bob
