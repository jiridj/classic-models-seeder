"""Tests for HubSpot data transformers."""

import pytest
from decimal import Decimal

from cmcli.hubspot.transformers import (
    HubSpotTransformer,
    generate_domain,
    generate_email,
    map_order_status_to_deal_stage,
)


class TestHelperFunctions:
    """Test helper functions for data transformation."""
    
    def test_generate_domain(self):
        """Test domain generation from company name."""
        assert generate_domain("Acme Corp") == "acme-corp.example.com"
        assert generate_domain("ABC Company, Inc.") == "abc-company-inc.example.com"
        assert generate_domain("Test & Co.") == "test-co.example.com"
        assert generate_domain("123 Industries") == "123-industries.example.com"
    
    def test_generate_email(self):
        """Test email generation from name and domain."""
        assert generate_email("John", "Doe", "acme.com") == "john.doe@acme.com"
        assert generate_email("Mary Jane", "Smith", "test.com") == "maryjane.smith@test.com"
        assert generate_email("Bob", "O'Brien", "company.com") == "bob.obrien@company.com"
    
    def test_map_order_status_to_deal_stage(self):
        """Test order status to deal stage mapping."""
        assert map_order_status_to_deal_stage("Shipped") == "closedwon"
        assert map_order_status_to_deal_stage("Resolved") == "closedwon"
        assert map_order_status_to_deal_stage("Cancelled") == "closedlost"
        assert map_order_status_to_deal_stage("On Hold") == "contractsent"
        assert map_order_status_to_deal_stage("Disputed") == "contractsent"
        assert map_order_status_to_deal_stage("In Process") == "presentationscheduled"
        assert map_order_status_to_deal_stage("Unknown") == "qualifiedtobuy"


class TestHubSpotTransformer:
    """Test HubSpot transformer class."""
    
    @pytest.fixture
    def transformer(self):
        """Create a transformer instance."""
        return HubSpotTransformer()
    
    @pytest.fixture
    def sample_customer(self):
        """Sample customer data."""
        return {
            "customerNumber": 103,
            "customerName": "Atelier graphique",
            "contactFirstName": "Carine",
            "contactLastName": "Schmitt",
            "phone": "40.32.2555",
            "addressLine1": "54, rue Royale",
            "addressLine2": None,
            "city": "Nantes",
            "state": None,
            "postalCode": "44000",
            "country": "France",
            "salesRepEmployeeNumber": 1370,
            "creditLimit": "21000.00"
        }
    
    @pytest.fixture
    def sample_order(self):
        """Sample order data."""
        return {
            "orderNumber": 10100,
            "orderDate": "2024-09-05",
            "requiredDate": "2024-09-12",
            "shippedDate": "2024-09-09",
            "status": "Shipped",
            "comments": None,
            "customerNumber": 103
        }
    
    @pytest.fixture
    def sample_order_details(self):
        """Sample order details data."""
        return [
            {
                "orderNumber": 10100,
                "productCode": "S18_1749",
                "quantityOrdered": 30,
                "priceEach": "136.00",
                "orderLineNumber": 3
            },
            {
                "orderNumber": 10100,
                "productCode": "S18_2248",
                "quantityOrdered": 50,
                "priceEach": "55.09",
                "orderLineNumber": 2
            }
        ]
    
    def test_transform_customer_to_company(self, transformer, sample_customer):
        """Test customer to company transformation."""
        result = transformer.transform_customer_to_company(sample_customer)
        
        assert result["name"] == "Atelier graphique"
        assert result["domain"] == "atelier-graphique.example.com"
        assert result["city"] == "Nantes"
        assert result["country"] == "France"
        assert result["phone"] == "40.32.2555"
        assert result["zip"] == "44000"
        assert result["address"] == "54, rue Royale"
        assert result["erp_customer_number"] == "103"
        assert result["credit_limit"] == "21000.00"
        assert result["sales_rep_employee_number"] == "1370"
        
        # Check that domain is cached
        assert transformer.customer_domains[103] == "atelier-graphique.example.com"
        assert transformer.customer_names[103] == "Atelier graphique"
    
    def test_transform_customer_to_contact(self, transformer, sample_customer):
        """Test customer to contact transformation."""
        # First transform to company to cache domain
        transformer.transform_customer_to_company(sample_customer)
        
        result = transformer.transform_customer_to_contact(sample_customer)
        
        assert result["firstname"] == "Carine"
        assert result["lastname"] == "Schmitt"
        assert result["email"] == "carine.schmitt@atelier-graphique.example.com"
        assert result["company"] == "Atelier graphique"
        assert result["phone"] == "40.32.2555"
        assert result["jobtitle"] == "Purchasing Manager"
        assert result["erp_customer_number"] == "103"
    
    def test_transform_order_to_deal(
        self,
        transformer,
        sample_customer,
        sample_order,
        sample_order_details
    ):
        """Test order to deal transformation."""
        # First transform customer to cache name
        transformer.transform_customer_to_company(sample_customer)
        
        result = transformer.transform_order_to_deal(
            sample_order,
            sample_order_details,
            []  # No payments
        )
        
        assert result["dealname"] == "Order 10100 - Atelier graphique"
        assert result["dealstage"] == "closedwon"
        assert result["closedate"] == "2024-09-09"
        assert result["pipeline"] == "default"
        assert result["erp_order_number"] == "10100"
        assert result["erp_customer_number"] == "103"
        
        # Check amount calculation: (30 * 136.00) + (50 * 55.09) = 4080 + 2754.5 = 6834.5
        expected_amount = Decimal("30") * Decimal("136.00") + Decimal("50") * Decimal("55.09")
        assert Decimal(result["amount"]) == expected_amount
    
    def test_derive_payment_status_paid(self, transformer):
        """Test payment status derivation - paid."""
        payments = [
            {"customerNumber": 103, "amount": "10000.00"}
        ]
        
        status = transformer._derive_payment_status(
            10100,
            103,
            Decimal("5000.00"),
            payments
        )
        
        assert status == "paid"
    
    def test_derive_payment_status_partial(self, transformer):
        """Test payment status derivation - partial."""
        payments = [
            {"customerNumber": 103, "amount": "2000.00"}
        ]
        
        status = transformer._derive_payment_status(
            10100,
            103,
            Decimal("5000.00"),
            payments
        )
        
        assert status == "partial"
    
    def test_derive_payment_status_pending(self, transformer):
        """Test payment status derivation - pending."""
        payments = []
        
        status = transformer._derive_payment_status(
            10100,
            103,
            Decimal("5000.00"),
            payments
        )
        
        assert status == "pending"
    
    def test_handle_missing_optional_fields(self, transformer):
        """Test handling of missing optional fields."""
        customer = {
            "customerNumber": 999,
            "customerName": "Test Company",
            "contactFirstName": "John",
            "contactLastName": "Doe",
            "phone": "555-1234",
            "addressLine1": "123 Main St",
            "addressLine2": None,
            "city": None,
            "state": None,
            "postalCode": None,
            "country": "USA",
            "salesRepEmployeeNumber": None,
            "creditLimit": None
        }
        
        result = transformer.transform_customer_to_company(customer)
        
        assert result["name"] == "Test Company"
        assert result["city"] == ""
        assert result["state"] == ""
        assert result["zip"] == ""
        assert result["credit_limit"] == "0"
        assert result["sales_rep_employee_number"] == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob
