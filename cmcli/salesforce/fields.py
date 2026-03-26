"""Salesforce custom field definitions for Classic Models integration."""

from typing import Dict, List, Any

# Account (Customer) Custom Fields
ACCOUNT_CUSTOM_FIELDS: List[Dict[str, Any]] = [
    {
        "fullName": "ERP_Customer_Number__c",
        "label": "ERP Customer Number",
        "type": "Text",
        "length": 50,
        "externalId": True,
        "unique": True,
        "required": False,
        "description": "Customer number from Classic Models ERP system. Used for data synchronization.",
    },
    {
        "fullName": "Credit_Limit__c",
        "label": "Credit Limit",
        "type": "Currency",
        "precision": 18,
        "scale": 2,
        "required": False,
        "description": "Customer credit limit from ERP system.",
    },
    {
        "fullName": "Sales_Rep_Employee_Number__c",
        "label": "Sales Rep Employee Number",
        "type": "Text",
        "length": 50,
        "required": False,
        "description": "Employee number of assigned sales representative.",
    },
]

# Contact (Employee) Custom Fields
CONTACT_CUSTOM_FIELDS: List[Dict[str, Any]] = [
    {
        "fullName": "ERP_Employee_Number__c",
        "label": "ERP Employee Number",
        "type": "Text",
        "length": 50,
        "externalId": True,
        "unique": True,
        "required": False,
        "description": "Employee number from Classic Models ERP system. Used for data synchronization.",
    },
    {
        "fullName": "Office_Code__c",
        "label": "Office Code",
        "type": "Text",
        "length": 10,
        "required": False,
        "description": "Office location code from ERP system.",
    },
    {
        "fullName": "Reports_To_Employee_Number__c",
        "label": "Reports To Employee Number",
        "type": "Text",
        "length": 50,
        "required": False,
        "description": "Employee number of manager/supervisor.",
    },
]

# Opportunity (Order) Custom Fields
OPPORTUNITY_CUSTOM_FIELDS: List[Dict[str, Any]] = [
    {
        "fullName": "ERP_Order_Number__c",
        "label": "ERP Order Number",
        "type": "Text",
        "length": 50,
        "externalId": True,
        "unique": True,
        "required": False,
        "description": "Order number from Classic Models ERP system. Used for data synchronization.",
    },
    {
        "fullName": "ERP_Customer_Number__c",
        "label": "ERP Customer Number",
        "type": "Text",
        "length": 50,
        "required": False,
        "description": "Customer number reference from ERP system.",
    },
    {
        "fullName": "Order_Date__c",
        "label": "Order Date",
        "type": "Date",
        "required": False,
        "description": "Original order date from ERP system.",
    },
    {
        "fullName": "Required_Date__c",
        "label": "Required Date",
        "type": "Date",
        "required": False,
        "description": "Customer requested delivery date.",
    },
    {
        "fullName": "Shipped_Date__c",
        "label": "Shipped Date",
        "type": "Date",
        "required": False,
        "description": "Actual shipment date.",
    },
    {
        "fullName": "Order_Status__c",
        "label": "Order Status",
        "type": "Picklist",
        "required": False,
        "description": "Order status from ERP system.",
        "valueSet": {
            "valueSetDefinition": {
                "sorted": False,
                "value": [
                    {"fullName": "Shipped", "default": False, "label": "Shipped"},
                    {"fullName": "Resolved", "default": False, "label": "Resolved"},
                    {"fullName": "Cancelled", "default": False, "label": "Cancelled"},
                    {"fullName": "On Hold", "default": False, "label": "On Hold"},
                    {"fullName": "Disputed", "default": False, "label": "Disputed"},
                    {"fullName": "In Process", "default": True, "label": "In Process"},
                ]
            }
        },
    },
    {
        "fullName": "Payment_Status__c",
        "label": "Payment Status",
        "type": "Picklist",
        "required": False,
        "description": "Payment status derived from payment records.",
        "valueSet": {
            "valueSetDefinition": {
                "sorted": False,
                "value": [
                    {"fullName": "Pending", "default": True, "label": "Pending"},
                    {"fullName": "Paid", "default": False, "label": "Paid"},
                    {"fullName": "Partial", "default": False, "label": "Partial"},
                    {"fullName": "Overdue", "default": False, "label": "Overdue"},
                ]
            }
        },
    },
    {
        "fullName": "Order_Comments__c",
        "label": "Order Comments",
        "type": "LongTextArea",
        "length": 32768,
        "visibleLines": 3,
        "required": False,
        "description": "Comments and notes from the order.",
    },
]


# Product2 (Product) Custom Fields
PRODUCT_CUSTOM_FIELDS: List[Dict[str, Any]] = [
    {
        "fullName": "ERP_Product_Code__c",
        "label": "ERP Product Code",
        "type": "Text",
        "length": 50,
        "externalId": True,
        "unique": True,
        "required": False,
        "description": "Product code from Classic Models ERP system. Used for data synchronization.",
    },
    {
        "fullName": "Product_Scale__c",
        "label": "Product Scale",
        "type": "Text",
        "length": 20,
        "required": False,
        "description": "Scale of the model (e.g., 1:10, 1:18).",
    },
    {
        "fullName": "Product_Vendor__c",
        "label": "Product Vendor",
        "type": "Text",
        "length": 100,
        "required": False,
        "description": "Vendor/manufacturer of the product.",
    },
    {
        "fullName": "Buy_Price__c",
        "label": "Buy Price",
        "type": "Currency",
        "precision": 18,
        "scale": 2,
        "required": False,
        "description": "Wholesale/buy price from vendor.",
    },
    {
        "fullName": "MSRP__c",
        "label": "MSRP",
        "type": "Currency",
        "precision": 18,
        "scale": 2,
        "required": False,
        "description": "Manufacturer's Suggested Retail Price.",
    },
    {
        "fullName": "Quantity_In_Stock__c",
        "label": "Quantity In Stock",
        "type": "Number",
        "precision": 18,
        "scale": 0,
        "required": False,
        "description": "Current inventory quantity.",
    },
]


def get_fields_for_object(sobject: str) -> List[Dict[str, Any]]:
    """Get custom field definitions for a Salesforce object.
    
    Args:
        sobject: Salesforce object type (Account, Contact, Opportunity)
        
    Returns:
        List of field definitions
        
    Raises:
        ValueError: If object type is not supported
    """
    field_map = {
        "Account": ACCOUNT_CUSTOM_FIELDS,
        "Contact": CONTACT_CUSTOM_FIELDS,
        "Opportunity": OPPORTUNITY_CUSTOM_FIELDS,
        "Product2": PRODUCT_CUSTOM_FIELDS,
    }
    
    if sobject not in field_map:
        raise ValueError(f"Unsupported object type: {sobject}")
    
    return field_map[sobject]


def get_all_custom_fields() -> Dict[str, List[Dict[str, Any]]]:
    """Get all custom field definitions.
    
    Returns:
        Dictionary mapping object types to field definitions
    """
    return {
        "Account": ACCOUNT_CUSTOM_FIELDS,
        "Contact": CONTACT_CUSTOM_FIELDS,
        "Opportunity": OPPORTUNITY_CUSTOM_FIELDS,
        "Product2": PRODUCT_CUSTOM_FIELDS,
    }


def get_external_id_field(sobject: str) -> str:
    """Get the external ID field name for an object.
    
    Args:
        sobject: Salesforce object type
        
    Returns:
        External ID field name
        
    Raises:
        ValueError: If object type is not supported
    """
    external_id_map = {
        "Account": "ERP_Customer_Number__c",
        "Contact": "ERP_Employee_Number__c",
        "Opportunity": "ERP_Order_Number__c",
        "Product2": "ERP_Product_Code__c",
    }
    
    if sobject not in external_id_map:
        raise ValueError(f"Unsupported object type: {sobject}")
    
    return external_id_map[sobject]


# Made with Bob