"""Data transformation from Classic Models to HubSpot format."""

import re
from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def generate_domain(company_name: str) -> str:
    """Generate a domain name from company name.
    
    Args:
        company_name: Company name
    
    Returns:
        Generated domain (e.g., "acme-corp.example.com")
    """
    # Convert to lowercase and replace spaces/special chars with hyphens
    domain = company_name.lower()
    domain = re.sub(r'[^a-z0-9]+', '-', domain)
    domain = domain.strip('-')
    return f"{domain}.example.com"


def generate_email(first_name: str, last_name: str, domain: str) -> str:
    """Generate an email address.
    
    Args:
        first_name: Contact first name
        last_name: Contact last name
        domain: Company domain
    
    Returns:
        Generated email address
    """
    # Remove spaces and special characters, keep only alphanumeric
    first = re.sub(r'[^a-z0-9]', '', first_name.lower())
    last = re.sub(r'[^a-z0-9]', '', last_name.lower())
    return f"{first}.{last}@{domain}"


def map_order_status_to_deal_stage(status: str) -> str:
    """Map Classic Models order status to HubSpot deal stage.
    
    Args:
        status: Order status from Classic Models
    
    Returns:
        HubSpot deal stage ID
    """
    status_mapping = {
        "Shipped": "closedwon",
        "Resolved": "closedwon",
        "Cancelled": "closedlost",
        "On Hold": "contractsent",
        "Disputed": "contractsent",
        "In Process": "presentationscheduled",
    }
    return status_mapping.get(status, "qualifiedtobuy")


class HubSpotTransformer:
    """Transform Classic Models data to HubSpot format."""
    
    def __init__(self):
        """Initialize transformer."""
        self.customer_domains: Dict[int, str] = {}
        self.customer_names: Dict[int, str] = {}
    
    def transform_customer_to_company(self, customer: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a Classic Models customer to HubSpot company.
        
        Args:
            customer: Customer record from Classic Models
        
        Returns:
            HubSpot company properties
        """
        customer_number = customer["customerNumber"]
        customer_name = customer["customerName"]
        
        # Generate and cache domain
        domain = generate_domain(customer_name)
        self.customer_domains[customer_number] = domain
        self.customer_names[customer_number] = customer_name
        
        properties = {
            "name": customer_name,
            "domain": domain,
            "city": customer.get("city") or "",
            "state": customer.get("state") or "",
            "country": customer.get("country") or "",
            "phone": customer.get("phone") or "",
            "zip": customer.get("postalCode") or "",
            "address": customer.get("addressLine1") or "",
            "erp_customer_number": str(customer_number),
            "credit_limit": str(customer.get("creditLimit") or "0"),
            "sales_rep_employee_number": str(customer.get("salesRepEmployeeNumber") or ""),
        }
        
        return properties
    
    def transform_customer_to_contact(self, customer: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a Classic Models customer to HubSpot contact.
        
        Args:
            customer: Customer record from Classic Models
        
        Returns:
            HubSpot contact properties
        """
        customer_number = customer["customerNumber"]
        first_name = customer.get("contactFirstName", "")
        last_name = customer.get("contactLastName", "")
        
        # Get or generate domain
        domain = self.customer_domains.get(
            customer_number,
            generate_domain(customer["customerName"])
        )
        
        # Generate email
        email = generate_email(first_name, last_name, domain)
        
        properties = {
            "firstname": first_name,
            "lastname": last_name,
            "email": email,
            "company": customer["customerName"],
            "phone": customer.get("phone") or "",
            "jobtitle": "Purchasing Manager",
            "erp_customer_number": str(customer_number),
        }
        
        return properties
    
    def transform_order_to_deal(
        self,
        order: Dict[str, Any],
        order_details: List[Dict[str, Any]],
        payments: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Transform a Classic Models order to HubSpot deal.
        
        Args:
            order: Order record from Classic Models
            order_details: Order detail records for this order
            payments: Payment records for this customer
        
        Returns:
            HubSpot deal properties
        """
        order_number = order["orderNumber"]
        customer_number = order["customerNumber"]
        
        # Calculate order total from order details
        total = sum(
            Decimal(str(detail["quantityOrdered"])) * Decimal(str(detail["priceEach"]))
            for detail in order_details
            if detail["orderNumber"] == order_number
        )
        
        # Get customer name
        customer_name = self.customer_names.get(customer_number, f"Customer {customer_number}")
        
        # Map status to deal stage
        deal_stage = map_order_status_to_deal_stage(order["status"])
        
        # Determine close date and convert to HubSpot timestamp format
        close_date_str = order.get("shippedDate") or order.get("orderDate") or ""
        # Convert YYYY-MM-DD to milliseconds since epoch (midnight UTC)
        if close_date_str:
            close_date_dt = datetime.strptime(close_date_str, "%Y-%m-%d")
            close_date_timestamp = int(close_date_dt.timestamp() * 1000)
        else:
            # Fallback to current date if no date available
            close_date_timestamp = int(datetime.now().timestamp() * 1000)
        
        # Derive payment status
        payment_status = self._derive_payment_status(order_number, customer_number, total, payments)
        
        properties = {
            "dealname": f"Order {order_number} - {customer_name}",
            "amount": str(total),
            "dealstage": deal_stage,
            "closedate": str(close_date_timestamp),
            "pipeline": "default",
            "erp_order_number": str(order_number),
            "erp_customer_number": str(customer_number),
            "payment_status": payment_status,
        }
        
        return properties
    
    def _derive_payment_status(
        self,
        order_number: int,
        customer_number: int,
        order_total: Decimal,
        payments: List[Dict[str, Any]],
    ) -> str:
        """Derive payment status for an order.
        
        Args:
            order_number: Order number
            customer_number: Customer number
            order_total: Total order amount
            payments: All payment records
        
        Returns:
            Payment status: 'paid', 'partial', 'pending', or 'overdue'
        """
        # Get payments for this customer
        customer_payments = [
            p for p in payments
            if p["customerNumber"] == customer_number
        ]
        
        if not customer_payments:
            return "pending"
        
        # Calculate total payments for customer
        total_paid = sum(
            Decimal(str(p["amount"]))
            for p in customer_payments
        )
        
        # Simple heuristic: if customer has paid more than order total, mark as paid
        # In reality, we'd need to track which payments apply to which orders
        if total_paid >= order_total:
            return "paid"
        elif total_paid > 0:
            return "partial"
        else:
            return "pending"


def batch_transform_customers_to_companies(
    customers: List[Dict[str, Any]],
    transformer: Optional[HubSpotTransformer] = None,
) -> List[Dict[str, Any]]:
    """Batch transform customers to companies.
    
    Args:
        customers: List of customer records
        transformer: Optional transformer instance to reuse
    
    Returns:
        List of HubSpot company property dictionaries
    """
    if transformer is None:
        transformer = HubSpotTransformer()
    
    return [
        transformer.transform_customer_to_company(customer)
        for customer in customers
    ]


def batch_transform_customers_to_contacts(
    customers: List[Dict[str, Any]],
    transformer: Optional[HubSpotTransformer] = None,
) -> List[Dict[str, Any]]:
    """Batch transform customers to contacts.
    
    Args:
        customers: List of customer records
        transformer: Optional transformer instance to reuse
    
    Returns:
        List of HubSpot contact property dictionaries
    """
    if transformer is None:
        transformer = HubSpotTransformer()
    
    return [
        transformer.transform_customer_to_contact(customer)
        for customer in customers
    ]


def batch_transform_orders_to_deals(
    orders: List[Dict[str, Any]],
    order_details: List[Dict[str, Any]],
    payments: List[Dict[str, Any]],
    transformer: Optional[HubSpotTransformer] = None,
) -> List[Dict[str, Any]]:
    """Batch transform orders to deals.
    
    Args:
        orders: List of order records
        order_details: List of all order detail records
        payments: List of all payment records
        transformer: Optional transformer instance to reuse
    
    Returns:
        List of HubSpot deal property dictionaries
    """
    if transformer is None:
        transformer = HubSpotTransformer()
    
    return [
        transformer.transform_order_to_deal(order, order_details, payments)
        for order in orders
    ]

# Made with Bob
