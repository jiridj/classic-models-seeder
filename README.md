# Classic Models Seeder

A Python CLI tool for seeding applications with the Classic Models demo dataset. Currently supports HubSpot CRM and Salesforce with plans to expand to additional platforms.

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/jiridj/classic-models-seeder.git
cd classic-models-seeder

# Install dependencies
pip install -r requirements.txt

# Install the CLI tool
pip install -e .
```

### Configuration

Create a `.env` file in the project root:

```bash
# HubSpot Configuration
HUBSPOT_ACCESS_TOKEN=pat-na1-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
HUBSPOT_ACCOUNT_ID=12345678

# Salesforce Configuration (SOAP API)
SALESFORCE_USERNAME=your_salesforce_username@example.com
SALESFORCE_PASSWORD=your_salesforce_password
SALESFORCE_SECURITY_TOKEN=your_security_token
SALESFORCE_INSTANCE_URL=https://your-instance.develop.my.salesforce.com
SALESFORCE_API_VERSION=v59.0

# Classic Models API (optional, for future features)
CLASSIC_MODELS_API_URL=http://localhost:8000/classic-models
CLASSIC_MODELS_USERNAME=demo
CLASSIC_MODELS_PASSWORD=demo123
```

See setup guides for detailed instructions:
- [HubSpot Setup Guide](docs/setup/HUBSPOT.md)
- [Salesforce Setup Guide](docs/setup/SALESFORCE.md)

### Usage

```bash
# Update timestamps in dataset to current dates
cmcli update

# HubSpot Commands
cmcli hubspot verify                    # Verify credentials and permissions
cmcli hubspot seed                      # Seed all data (companies, contacts, deals)
cmcli hubspot seed --companies-only     # Seed only companies
cmcli hubspot seed --contacts-only      # Seed only contacts
cmcli hubspot seed --deals-only         # Seed only deals

# Salesforce Commands
cmcli salesforce verify                      # Verify credentials and permissions
cmcli salesforce setup-fields                # List custom fields to create manually
cmcli salesforce seed                        # Seed all data
cmcli salesforce seed --accounts-only        # Seed only accounts
cmcli salesforce seed --contacts-only        # Seed only contacts
cmcli salesforce seed --opportunities-only   # Seed only opportunities
cmcli salesforce seed --products-only        # Seed only products
```

## What Gets Seeded

### HubSpot CRM
| HubSpot Object | Source Data | Count |
|----------------|-------------|-------|
| Companies | Classic Models customers | 122 |
| Contacts | Customer contact information | 122 |
| Deals | Classic Models orders | 326 |

### Salesforce
| Salesforce Object | Source Data | Count |
|-------------------|-------------|-------|
| Accounts | Classic Models customers | 122 |
| Contacts | Classic Models employees | 23 |
| Opportunities | Classic Models orders | 326 |
| Products (Product2) | Classic Models products | 110 |
| OpportunityLineItems | Order details | 2,996 |

## Features

- ✅ **Idempotent seeding** - Safe to run multiple times, updates existing records
- ✅ **Rate limiting** - Automatic handling of API rate limits with informative errors
- ✅ **Custom fields** - Manual creation with detailed setup guide
- ✅ **Relationships** - Links contacts to accounts, opportunities to accounts/contacts
- ✅ **Progress tracking** - Real-time progress bars and status updates
- ✅ **Error handling** - Graceful handling of API errors with retry logic
- ✅ **Product seeding** - Full product catalog with pricebook entries and line items

## Data Mappings

### HubSpot CRM

**Companies ← Customers**
- Standard fields: name, domain, city, state, country, phone, zip, address
- Custom fields: `erp_customer_number`, `credit_limit`, `sales_rep_employee_number`

**Contacts ← Customer Contacts**
- Standard fields: firstname, lastname, email, company, phone, jobtitle
- Custom fields: `erp_customer_number`

**Deals ← Orders**
- Standard fields: dealname, amount, dealstage, closedate, pipeline
- Custom fields: `erp_order_number`, `erp_customer_number`, `payment_status`

### Salesforce

**Accounts ← Customers**
- Standard fields: Name, BillingCity, BillingState, BillingCountry, Phone, BillingPostalCode, BillingStreet, Website
- Custom fields: `ERP_Customer_Number__c`, `Credit_Limit__c`, `Sales_Rep_Employee_Number__c`

**Contacts ← Employees**
- Standard fields: FirstName, LastName, Email, Phone, Title
- Custom fields: `ERP_Employee_Number__c`, `Office_Code__c`, `Reports_To_Employee_Number__c`

**Opportunities ← Orders**
- Standard fields: Name, Amount, StageName, CloseDate, Pricebook2Id
- Custom fields: `ERP_Order_Number__c`, `ERP_Customer_Number__c`, `Order_Date__c`, `Required_Date__c`, `Shipped_Date__c`, `Order_Status__c`, `Payment_Status__c`, `Order_Comments__c`

**Products (Product2) ← Products**
- Standard fields: Name, ProductCode, Description, IsActive, Family
- Custom fields: `ERP_Product_Code__c`, `Product_Scale__c`, `Product_Vendor__c`, `MSRP__c`, `Buy_Price__c`

**OpportunityLineItems ← Order Details**
- Standard fields: OpportunityId, PricebookEntryId, Quantity, UnitPrice, Description
- Links products to opportunities with quantities and prices

## Documentation

- [Project Overview](specs/PROJECT.md) - Purpose and architecture
- [HubSpot Setup](specs/setup/HUBSPOT.md) - Detailed HubSpot setup instructions
- [Salesforce Setup](specs/setup/SALESFORCE.md) - Detailed Salesforce setup instructions
- [Classic Models API](specs/api/CLASSIC-MODELS.md) - ERP API documentation
- [Architecture Guide](docs/architecture.md) - Technical architecture details
- [API Reference](docs/api-reference.md) - CLI command reference
- [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions
- [Salesforce Implementation Plan](docs/salesforce-implementation-plan.md) - Technical implementation details

## Requirements

- Python 3.9 or higher
- **For HubSpot**: HubSpot account (free tier supported) with API access token
- **For Salesforce**: Salesforce Developer Edition (free) with SOAP API enabled

## Development

```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run with verbose logging
cmcli --verbose hubspot seed
```

## Supported Applications

- ✅ **HubSpot CRM** - Companies, Contacts, Deals
- ✅ **Salesforce** - Accounts, Contacts, Opportunities, Products, Line Items
- 🔜 **Stripe** - Coming soon
- 🔜 **Trello** - Coming soon

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please see CONTRIBUTING.md for guidelines.

## Support

- 📖 [Documentation](docs/)
- 🐛 [Issue Tracker](https://github.com/jiridj/classic-models-seeder/issues)
- 💬 [Discussions](https://github.com/jiridj/classic-models-seeder/discussions)