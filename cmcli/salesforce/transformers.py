"""Data transformation from Classic Models to Salesforce format (MVP version)."""

import re
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

from cmcli.utils.logging import get_logger

logger = get_logger("salesforce.transformers")


def normalize_country_name(country: str) -> str:
    """Normalize country names to Salesforce-compatible format.
    
    Salesforce requires full country names when State and Country Picklists are enabled.
    
    Args:
        country: Country name from Classic Models
        
    Returns:
        Normalized country name
    """
    # Map common abbreviations and variations to full names
    country_mapping = {
        "USA": "United States",
        "UK": "United Kingdom",
        # Add more mappings if needed
    }
    
    return country_mapping.get(country, country)


def generate_website(company_name: str) -> str:
    """Generate a website URL from company name.
    
    Args:
        company_name: Company name
        
    Returns:
        Website URL
    """
    # Simple: lowercase, replace spaces with hyphens, add .com
    domain = re.sub(r'[^a-z0-9]+', '-', company_name.lower()).strip('-')
    return f"https://www.{domain}.com"


def map_order_status_to_stage(status: str) -> Tuple[str, int]:
    """Map order status to Salesforce Opportunity stage and probability.
    
    Args:
        status: Order status from Classic Models
        
    Returns:
        Tuple of (stage_name, probability)
    """
    mapping = {
        "Shipped": ("Closed Won", 100),
        "Resolved": ("Closed Won", 100),
        "Cancelled": ("Closed Lost", 0),
        "On Hold": ("Negotiation/Review", 60),
        "Disputed": ("Negotiation/Review", 60),
        "In Process": ("Proposal/Price Quote", 75),
    }
    
    return mapping.get(status, ("Proposal/Price Quote", 50))


class SalesforceTransformer:
    """Transform Classic Models data to Salesforce format (MVP)."""
    
    def transform_customer_to_account(self, customer: Dict[str, Any]) -> Dict[str, Any]:
        """Transform customer to Salesforce Account.
        
        Args:
            customer: Customer data from Classic Models
            
        Returns:
            Salesforce Account data
        """
        # Build billing address
        billing_street = customer.get("addressLine1", "")
        if customer.get("addressLine2"):
            billing_street += f"\n{customer['addressLine2']}"
        
        # Note: We skip BillingState and BillingCountry because Salesforce has State/Country
        # Picklists enabled which requires specific codes. The Classic Models data has free-form
        # names that don't match Salesforce's validation. For a production system, you'd need
        # comprehensive mapping functions. For this demo, we'll focus on the core data.
        account = {
            "Name": customer["customerName"],
            "BillingStreet": billing_street or None,
            "BillingCity": customer.get("city"),
            # "BillingState": customer.get("state"),  # Skipped due to Salesforce validation
            "BillingPostalCode": customer.get("postalCode"),
            # "BillingCountry": country,  # Skipped due to Salesforce validation
            "Phone": customer.get("phone"),
            "Website": generate_website(customer["customerName"]),
            # Custom fields (NOTE: ERP_Customer_Number__c is NOT included here - it's used as the external ID in upsert)
            "Credit_Limit__c": float(customer["creditLimit"]) if customer.get("creditLimit") else None,
            "Sales_Rep_Employee_Number__c": str(customer["salesRepEmployeeNumber"]) if customer.get("salesRepEmployeeNumber") else None,
        }
        
        # Remove None values
        return {k: v for k, v in account.items() if v is not None}
    
    def transform_customer_contact_to_contact(
        self,
        customer: Dict[str, Any],
        account_id: str
    ) -> Dict[str, Any]:
        """Transform customer contact info to Salesforce Contact.
        
        Args:
            customer: Customer data from Classic Models (contains contact info)
            account_id: Salesforce Account ID to link to
            
        Returns:
            Salesforce Contact data
        """
        contact = {
            "FirstName": customer.get("contactFirstName", ""),
            "LastName": customer["contactLastName"],
            "Phone": customer.get("phone"),
            "AccountId": account_id,
            # Note: No email in customer data, and no custom fields needed for customer contacts
        }
        
        # Remove None values
        return {k: v for k, v in contact.items() if v is not None}
    
    def transform_employee_to_contact(
        self,
        employee: Dict[str, Any],
        account_id: str | None = None
    ) -> Dict[str, Any]:
        """Transform employee to Salesforce Contact.
        
        Args:
            employee: Employee data from Classic Models
            account_id: Optional Salesforce Account ID to link to
            
        Returns:
            Salesforce Contact data
        """
        contact = {
            "FirstName": employee.get("firstName", ""),
            "LastName": employee["lastName"],
            "Email": employee["email"],
            "Phone": employee.get("extension"),
            "Title": employee.get("jobTitle"),
            # Custom fields (NOTE: ERP_Employee_Number__c is NOT included here - it's used as the external ID in upsert)
            "Office_Code__c": employee.get("officeCode"),
            "Reports_To_Employee_Number__c": str(employee["reportsTo"]) if employee.get("reportsTo") else None,
        }
        
        if account_id:
            contact["AccountId"] = account_id
        
        # Remove None values
        return {k: v for k, v in contact.items() if v is not None}
    
    def transform_order_to_opportunity(
        self,
        order: Dict[str, Any],
        order_details: List[Dict[str, Any]],
        customer: Dict[str, Any],
        account_id: str,
        pricebook_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transform order to Salesforce Opportunity.
        
        Args:
            order: Order data from Classic Models
            order_details: Order detail records for this order
            customer: Customer data
            account_id: Salesforce Account ID
            pricebook_id: Optional Pricebook2 ID (required for adding products)
            
        Returns:
            Salesforce Opportunity data
        """
        # Calculate amount from order details
        amount = sum(
            float(detail.get("quantityOrdered", 0)) * float(detail.get("priceEach", 0))
            for detail in order_details
        )
        
        # Map status to stage
        stage, probability = map_order_status_to_stage(order["status"])
        
        # Determine close date
        close_date = order.get("shippedDate") or order.get("orderDate")
        
        opportunity = {
            "Name": f"Order {order['orderNumber']} - {customer['customerName']}",
            "AccountId": account_id,
            "Amount": round(amount, 2),
            "StageName": stage,
            "Probability": probability,
            "CloseDate": close_date,
            "Type": "New Business",
            # Custom fields (NOTE: ERP_Order_Number__c is NOT included here - it's used as the external ID in upsert)
            "ERP_Customer_Number__c": str(order["customerNumber"]),
            "Order_Date__c": order.get("orderDate"),
            "Required_Date__c": order.get("requiredDate"),
            "Shipped_Date__c": order.get("shippedDate"),
            "Order_Status__c": order["status"],
            "Order_Comments__c": order.get("comments"),
        }
        
        # Add pricebook if provided (required for adding products)
        if pricebook_id:
            opportunity["Pricebook2Id"] = pricebook_id
        
        # Remove None values
        return {k: v for k, v in opportunity.items() if v is not None}
    
    def transform_product_to_product2(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Transform product to Salesforce Product2.
        
        Args:
            product: Product data from Classic Models
            
        Returns:
            Salesforce Product2 data
        """
        product2 = {
            "Name": product["productName"],
            "ProductCode": product["productCode"],  # Standard field
            "Description": product.get("productDescription"),
            "Family": product.get("productLine"),  # Product line maps to Family
            "IsActive": True,
            # Custom fields (NOTE: ERP_Product_Code__c is NOT included here - it's used as the external ID in upsert)
            "Product_Scale__c": product.get("productScale"),
            "Product_Vendor__c": product.get("productVendor"),
            "Buy_Price__c": float(product["buyPrice"]) if product.get("buyPrice") else None,
            "MSRP__c": float(product["MSRP"]) if product.get("MSRP") else None,
            "Quantity_In_Stock__c": int(product["quantityInStock"]) if product.get("quantityInStock") else None,
        }
        
        # Remove None values
        return {k: v for k, v in product2.items() if v is not None}
    
    def transform_order_detail_to_line_item(
        self,
        order_detail: Dict[str, Any],
        opportunity_id: str,
        pricebook_entry_id: str
    ) -> Dict[str, Any]:
        """Transform order detail to Salesforce OpportunityLineItem.
        
        Args:
            order_detail: Order detail data from Classic Models
            opportunity_id: Salesforce Opportunity ID
            pricebook_entry_id: Salesforce PricebookEntry ID
            
        Returns:
            Salesforce OpportunityLineItem data
        """
        line_item = {
            "OpportunityId": opportunity_id,
            "PricebookEntryId": pricebook_entry_id,
            "Quantity": float(order_detail["quantityOrdered"]),
            "UnitPrice": float(order_detail["priceEach"]),
            "Description": f"Line {order_detail.get('orderLineNumber', '')}",
        }
        
        # Remove None values
        return {k: v for k, v in line_item.items() if v is not None}


# Made with Bob