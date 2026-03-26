"""Salesforce seeding orchestration (MVP version)."""

from typing import Dict, Any, List, Optional
import click

from cmcli.salesforce.client import SalesforceClient
from cmcli.salesforce.transformers import SalesforceTransformer
from cmcli.salesforce.fields import get_external_id_field
from cmcli.data.loader import DataLoader
from cmcli.utils.logging import get_logger

logger = get_logger("salesforce.seeder")


class SalesforceSeeder:
    """Orchestrate seeding of Salesforce with Classic Models data (MVP)."""
    
    def __init__(self, client: SalesforceClient, data_loader: DataLoader):
        """Initialize seeder.
        
        Args:
            client: Salesforce API client
            data_loader: Data loader for Classic Models data
        """
        self.client = client
        self.data_loader = data_loader
        self.transformer = SalesforceTransformer()
        
        # Cache for IDs
        self.account_ids: Dict[str, str] = {}  # customer_number -> account_id
        self.contact_ids: Dict[str, str] = {}  # employee_number -> contact_id
        self.product_ids: Dict[str, str] = {}  # product_code -> product_id
        self.pricebook_entry_ids: Dict[str, str] = {}  # product_code -> pricebook_entry_id
        self.opportunity_ids: Dict[str, str] = {}  # order_number -> opportunity_id
    
    def seed_accounts(self, customers: Optional[List[Dict[str, Any]]] = None) -> tuple[int, int]:
        """Seed accounts from customers and their associated contacts.
        
        Args:
            customers: Optional list of customers (loads from data if not provided)
            
        Returns:
            Tuple of (accounts_count, contacts_count)
        """
        if customers is None:
            customers = self.data_loader.load_customers()
        
        account_count = 0
        contact_count = 0
        
        with click.progressbar(
            customers,
            label='Seeding accounts & contacts',
            show_pos=True
        ) as bar:
            for customer in bar:
                try:
                    customer_number = str(customer["customerNumber"])
                    account_data = self.transformer.transform_customer_to_account(customer)
                    
                    # Upsert account using external ID
                    result = self.client.upsert_record(
                        sobject="Account",
                        external_id_field=get_external_id_field("Account"),
                        external_id=customer_number,
                        data=account_data
                    )
                    
                    # Cache the account ID
                    account_id = result["id"]
                    self.account_ids[customer_number] = account_id
                    
                    action = "Created" if result.get("created") else "Updated"
                    logger.debug(f"{action} account for customer {customer_number}")
                    account_count += 1
                    
                    # Create contact for this customer
                    try:
                        contact_data = self.transformer.transform_customer_contact_to_contact(
                            customer, account_id
                        )
                        
                        # Use customer number as external ID for customer contacts
                        contact_result = self.client.upsert_record(
                            sobject="Contact",
                            external_id_field=get_external_id_field("Contact"),
                            external_id=f"CUST-{customer_number}",  # Prefix to distinguish from employee contacts
                            data=contact_data
                        )
                        
                        contact_action = "Created" if contact_result.get("created") else "Updated"
                        logger.debug(f"{contact_action} contact for customer {customer_number}")
                        contact_count += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to create contact for customer {customer_number}: {e}")
                    
                except Exception as e:
                    logger.error(f"Failed to seed account for customer {customer.get('customerNumber')}: {e}")
        
        click.echo(f"\n✓ Seeded {account_count} accounts and {contact_count} contacts")
        return account_count, contact_count
    
    def seed_contacts(self) -> int:
        """Seed contacts - this is now handled by seed_accounts.
        
        Note: In the Classic Models dataset, employees are sales reps (not contacts).
        Contacts are the customer contact persons, which are created alongside accounts.
        
        Returns:
            0 (for backward compatibility)
        """
        click.echo("Note: Contacts are created with accounts (customer contact persons)")
        return 0
    
    def seed_products(self, products: Optional[List[Dict[str, Any]]] = None) -> int:
        """Seed products and create pricebook entries.
        
        Args:
            products: Optional list of products (loads from data if not provided)
            
        Returns:
            Number of products created/updated
        """
        if products is None:
            products = self.data_loader.load_products()
        
        # Get standard pricebook ID
        try:
            standard_pricebook_id = self.client.get_standard_pricebook_id()
        except Exception as e:
            logger.error(f"Failed to get standard pricebook: {e}")
            click.echo("✗ Could not find standard pricebook")
            return 0
        
        count = 0
        with click.progressbar(
            products,
            label='Seeding products           ',
            show_pos=True
        ) as bar:
            for product in bar:
                try:
                    product_code = str(product["productCode"])
                    product_data = self.transformer.transform_product_to_product2(product)
                    
                    # Upsert product using external ID
                    result = self.client.upsert_record(
                        sobject="Product2",
                        external_id_field=get_external_id_field("Product2"),
                        external_id=product_code,
                        data=product_data
                    )
                    
                    # Cache the product ID
                    product_id = result["id"]
                    self.product_ids[product_code] = product_id
                    
                    action = "Created" if result.get("created") else "Updated"
                    logger.debug(f"{action} product {product_code}")
                    
                    # Create or find pricebook entry
                    try:
                        pricebook_entry_id = self.client.find_pricebook_entry(
                            standard_pricebook_id, product_id
                        )
                        
                        if not pricebook_entry_id:
                            # Create pricebook entry with MSRP as unit price
                            unit_price = float(product.get("MSRP", product.get("buyPrice", 0)))
                            pricebook_entry_id = self.client.create_pricebook_entry(
                                pricebook_id=standard_pricebook_id,
                                product_id=product_id,
                                unit_price=unit_price
                            )
                            logger.debug(f"Created pricebook entry for product {product_code}")
                        
                        # Cache pricebook entry ID
                        self.pricebook_entry_ids[product_code] = pricebook_entry_id
                        
                    except Exception as e:
                        logger.error(f"Failed to create pricebook entry for product {product_code}: {e}")
                    
                    count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to seed product {product.get('productCode')}: {e}")
        
        click.echo(f"\n✓ Seeded {count} products")
        return count
    
    def seed_opportunities(self, orders: Optional[List[Dict[str, Any]]] = None) -> int:
        """Seed opportunities from orders (MVP - simple version).
        
        Args:
            orders: Optional list of orders (loads from data if not provided)
            
        Returns:
            Number of opportunities created/updated
        """
        if orders is None:
            orders = self.data_loader.load_orders()
        
        # Get standard pricebook ID (needed for adding products to opportunities)
        try:
            standard_pricebook_id = self.client.get_standard_pricebook_id()
        except Exception as e:
            logger.error(f"Could not get standard pricebook: {e}")
            standard_pricebook_id = None
        
        # Load related data
        order_details = self.data_loader.load_order_details()
        customers = self.data_loader.load_customers()
        
        # Build lookup maps
        details_by_order = {}
        for detail in order_details:
            order_num = detail["orderNumber"]
            if order_num not in details_by_order:
                details_by_order[order_num] = []
            details_by_order[order_num].append(detail)
        
        customers_by_number = {c["customerNumber"]: c for c in customers}
        
        count = 0
        with click.progressbar(
            orders,
            label='Seeding opportunities      ',
            show_pos=True
        ) as bar:
            for order in bar:
                try:
                    order_number = str(order["orderNumber"])
                    customer_number = str(order["customerNumber"])
                    
                    # Get account ID (load if not cached)
                    if customer_number not in self.account_ids:
                        account = self._find_account_by_erp_id(customer_number)
                        if account:
                            self.account_ids[customer_number] = account["Id"]
                    
                    if customer_number not in self.account_ids:
                        logger.debug(f"Account not found for customer {customer_number}, skipping order {order_number}")
                        continue
                    
                    account_id = self.account_ids[customer_number]
                    customer = customers_by_number.get(order["customerNumber"])
                    if not customer:
                        logger.debug(f"Customer {customer_number} not found, skipping order {order_number}")
                        continue
                        
                    details = details_by_order.get(order["orderNumber"], [])
                    
                    opportunity_data = self.transformer.transform_order_to_opportunity(
                        order=order,
                        order_details=details,
                        customer=customer,
                        account_id=account_id,
                        pricebook_id=standard_pricebook_id
                    )
                    
                    # Upsert using external ID
                    result = self.client.upsert_record(
                        sobject="Opportunity",
                        external_id_field=get_external_id_field("Opportunity"),
                        external_id=order_number,
                        data=opportunity_data
                    )
                    
                    # Cache the opportunity ID
                    opportunity_id = result["id"]
                    self.opportunity_ids[order_number] = opportunity_id
                    
                    action = "Created" if result.get("created") else "Updated"
                    logger.debug(f"{action} opportunity for order {order_number}")
                    count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to seed opportunity for order {order.get('orderNumber')}: {e}")
        
        click.echo(f"\n✓ Seeded {count} opportunities")
        return count
    
    def seed_opportunity_line_items(self, order_details: Optional[List[Dict[str, Any]]] = None) -> int:
        """Seed opportunity line items (products on opportunities).
        
        Args:
            order_details: Optional list of order details (loads from data if not provided)
            
        Returns:
            Number of line items created
        """
        if order_details is None:
            order_details = self.data_loader.load_order_details()
        
        count = 0
        skipped = 0
        
        with click.progressbar(
            order_details,
            label='Seeding opportunity products',
            show_pos=True
        ) as bar:
            for detail in bar:
                try:
                    order_number = str(detail["orderNumber"])
                    product_code = str(detail["productCode"])
                    
                    # Get opportunity ID
                    if order_number not in self.opportunity_ids:
                        # Try to find it
                        opp = self._find_opportunity_by_erp_id(order_number)
                        if opp:
                            self.opportunity_ids[order_number] = opp["Id"]
                    
                    if order_number not in self.opportunity_ids:
                        logger.debug(f"Opportunity not found for order {order_number}, skipping line item")
                        skipped += 1
                        continue
                    
                    # Get pricebook entry ID
                    if product_code not in self.pricebook_entry_ids:
                        logger.debug(f"Product {product_code} not found, skipping line item")
                        skipped += 1
                        continue
                    
                    opportunity_id = self.opportunity_ids[order_number]
                    pricebook_entry_id = self.pricebook_entry_ids[product_code]
                    
                    # Transform to line item
                    line_item_data = self.transformer.transform_order_detail_to_line_item(
                        order_detail=detail,
                        opportunity_id=opportunity_id,
                        pricebook_entry_id=pricebook_entry_id
                    )
                    
                    # Create line item (no upsert for line items, they're unique by opportunity+product)
                    # First check if it exists
                    existing = self.client.query(
                        f"SELECT Id FROM OpportunityLineItem "
                        f"WHERE OpportunityId = '{opportunity_id}' "
                        f"AND PricebookEntryId = '{pricebook_entry_id}' "
                        f"LIMIT 1"
                    )
                    
                    if existing:
                        # Update existing - only update quantity and price (OpportunityId and PricebookEntryId are read-only)
                        update_data = {
                            "Quantity": line_item_data["Quantity"],
                            "UnitPrice": line_item_data["UnitPrice"],
                        }
                        if "Description" in line_item_data:
                            update_data["Description"] = line_item_data["Description"]
                        
                        self.client.update_record(
                            "OpportunityLineItem",
                            existing[0]["Id"],
                            update_data
                        )
                        logger.debug(f"Updated line item for order {order_number}, product {product_code}")
                    else:
                        # Create new
                        self.client.create_record("OpportunityLineItem", line_item_data)
                        logger.debug(f"Created line item for order {order_number}, product {product_code}")
                    
                    count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to seed line item for order {detail.get('orderNumber')}, product {detail.get('productCode')}: {e}")
                    skipped += 1
        
        click.echo(f"\n✓ Seeded {count} opportunity line items ({skipped} skipped)")
        return count
    
    def _find_account_by_erp_id(self, erp_customer_number: str) -> Optional[Dict[str, Any]]:
        """Find account by ERP customer number.
        
        Args:
            erp_customer_number: ERP customer number
            
        Returns:
            Account record or None
        """
        try:
            soql = f"SELECT Id FROM Account WHERE ERP_Customer_Number__c = '{erp_customer_number}' LIMIT 1"
            results = self.client.query(soql)
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Error finding account: {e}")
            return None
    
    def _find_opportunity_by_erp_id(self, erp_order_number: str) -> Optional[Dict[str, Any]]:
        """Find opportunity by ERP order number.
        
        Args:
            erp_order_number: ERP order number
            
        Returns:
            Opportunity record or None
        """
        try:
            soql = f"SELECT Id FROM Opportunity WHERE ERP_Order_Number__c = '{erp_order_number}' LIMIT 1"
            results = self.client.query(soql)
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Error finding opportunity: {e}")
            return None
    
    def seed_all(self) -> Dict[str, int]:
        """Seed all objects in correct order.
        
        Returns:
            Dictionary with counts for each object type
        """
        click.echo("\n=== Seeding Salesforce ===\n")
        
        # Seed accounts and customer contacts
        account_count, contact_count = self.seed_accounts()
        
        # Seed products and pricebook entries
        product_count = self.seed_products()
        
        # Seed opportunities
        opportunity_count = self.seed_opportunities()
        
        # Seed opportunity line items (products on opportunities)
        line_item_count = self.seed_opportunity_line_items()
        
        results = {
            "accounts": account_count,
            "contacts": contact_count,
            "products": product_count,
            "opportunities": opportunity_count,
            "line_items": line_item_count,
        }
        
        click.echo(f"\n✓ Seeding complete!")
        click.echo(f"  Accounts: {account_count}")
        click.echo(f"  Contacts: {contact_count} (customer contact persons)")
        click.echo(f"  Products: {product_count}")
        click.echo(f"  Opportunities: {opportunity_count}")
        click.echo(f"  Opportunity Products: {line_item_count}")
        
        return results


# Made with Bob