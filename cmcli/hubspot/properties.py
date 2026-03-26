"""HubSpot custom property definitions."""

from typing import Dict, List, Any


# Custom property definitions for Companies
COMPANY_PROPERTIES = [
    {
        "name": "erp_customer_number",
        "label": "ERP Customer Number",
        "type": "string",
        "fieldType": "text",
        "groupName": "companyinformation",
        "description": "Customer number from Classic Models ERP",
        "options": [],
    },
    {
        "name": "credit_limit",
        "label": "Credit Limit",
        "type": "number",
        "fieldType": "number",
        "groupName": "companyinformation",
        "description": "Customer credit limit from ERP",
        "options": [],
    },
    {
        "name": "sales_rep_employee_number",
        "label": "Sales Rep Employee Number",
        "type": "string",
        "fieldType": "text",
        "groupName": "companyinformation",
        "description": "Assigned sales representative employee number",
        "options": [],
    },
]


# Custom property definitions for Contacts
CONTACT_PROPERTIES = [
    {
        "name": "erp_customer_number",
        "label": "ERP Customer Number",
        "type": "string",
        "fieldType": "text",
        "groupName": "contactinformation",
        "description": "Associated customer number from Classic Models ERP",
        "options": [],
    },
]


# Custom property definitions for Deals
DEAL_PROPERTIES = [
    {
        "name": "erp_order_number",
        "label": "ERP Order Number",
        "type": "string",
        "fieldType": "text",
        "groupName": "dealinformation",
        "description": "Order number from Classic Models ERP",
        "options": [],
    },
    {
        "name": "erp_customer_number",
        "label": "ERP Customer Number",
        "type": "string",
        "fieldType": "text",
        "groupName": "dealinformation",
        "description": "Customer reference from ERP",
        "options": [],
    },
    {
        "name": "payment_status",
        "label": "Payment Status",
        "type": "enumeration",
        "fieldType": "select",
        "groupName": "dealinformation",
        "description": "Payment status for this order",
        "options": [
            {"label": "Pending", "value": "pending"},
            {"label": "Paid", "value": "paid"},
            {"label": "Partial", "value": "partial"},
            {"label": "Overdue", "value": "overdue"},
        ],
    },
    {
        "name": "payment_link",
        "label": "Payment Link",
        "type": "string",
        "fieldType": "text",
        "groupName": "dealinformation",
        "description": "Stripe payment link URL",
        "options": [],
    },
]


# Custom property definitions for Products
PRODUCT_PROPERTIES = [
    {
        "name": "erp_product_code",
        "label": "ERP Product Code",
        "type": "string",
        "fieldType": "text",
        "groupName": "productinformation",
        "description": "Product code from Classic Models ERP",
        "options": [],
    },
    {
        "name": "product_line",
        "label": "Product Line",
        "type": "string",
        "fieldType": "text",
        "groupName": "productinformation",
        "description": "Product line category",
        "options": [],
    },
    {
        "name": "product_scale",
        "label": "Product Scale",
        "type": "string",
        "fieldType": "text",
        "groupName": "productinformation",
        "description": "Scale of the model (e.g., 1:10, 1:24)",
        "options": [],
    },
    {
        "name": "product_vendor",
        "label": "Product Vendor",
        "type": "string",
        "fieldType": "text",
        "groupName": "productinformation",
        "description": "Vendor/manufacturer of the product",
        "options": [],
    },
    {
        "name": "quantity_in_stock",
        "label": "Quantity in Stock",
        "type": "number",
        "fieldType": "number",
        "groupName": "productinformation",
        "description": "Current inventory quantity",
        "options": [],
    },
    {
        "name": "buy_price",
        "label": "Buy Price",
        "type": "number",
        "fieldType": "number",
        "groupName": "productinformation",
        "description": "Wholesale/buy price",
        "options": [],
    },
    {
        "name": "msrp",
        "label": "MSRP",
        "type": "number",
        "fieldType": "number",
        "groupName": "productinformation",
        "description": "Manufacturer's Suggested Retail Price",
        "options": [],
    },
]


def get_properties_for_object(object_type: str) -> List[Dict[str, Any]]:
    """Get custom property definitions for a HubSpot object type.
    
    Args:
        object_type: HubSpot object type ('companies', 'contacts', 'deals', 'products')
    
    Returns:
        List of property definitions
    
    Raises:
        ValueError: If object_type is not supported
    """
    if object_type == "companies":
        return COMPANY_PROPERTIES
    elif object_type == "contacts":
        return CONTACT_PROPERTIES
    elif object_type == "deals":
        return DEAL_PROPERTIES
    elif object_type == "products":
        return PRODUCT_PROPERTIES
    else:
        raise ValueError(f"Unsupported object type: {object_type}")


def get_all_properties() -> Dict[str, List[Dict[str, Any]]]:
    """Get all custom property definitions.
    
    Returns:
        Dictionary mapping object types to their property definitions
    """
    return {
        "companies": COMPANY_PROPERTIES,
        "contacts": CONTACT_PROPERTIES,
        "deals": DEAL_PROPERTIES,
        "products": PRODUCT_PROPERTIES,
    }

# Made with Bob
