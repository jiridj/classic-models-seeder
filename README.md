# Classic Models Seeder

A Python CLI tool for seeding applications with the Classic Models demo dataset. Currently supports HubSpot CRM with plans to expand to additional platforms.

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

# Classic Models API (optional, for future features)
CLASSIC_MODELS_API_URL=http://localhost:8000/classic-models
CLASSIC_MODELS_USERNAME=demo
CLASSIC_MODELS_PASSWORD=demo123
```

See [HubSpot Setup Guide](specs/setup/HUBSPOT.md) for detailed instructions on obtaining credentials.

### Usage

```bash
# Update timestamps in dataset to current dates
cmcli update

# Verify HubSpot credentials and permissions
cmcli hubspot verify

# Seed all data to HubSpot (companies, contacts, deals)
cmcli hubspot seed

# Seed only specific object types
cmcli hubspot seed --companies-only
cmcli hubspot seed --contacts-only
cmcli hubspot seed --deals-only
```

## What Gets Seeded

| HubSpot Object | Source Data | Count |
|----------------|-------------|-------|
| Companies | Classic Models customers | 122 |
| Contacts | Customer contact information | 122 |
| Deals | Classic Models orders | 326 |

## Features

- ✅ **Idempotent seeding** - Safe to run multiple times, updates existing records
- ✅ **Rate limiting** - Automatic handling of API rate limits (100 req/10s)
- ✅ **Custom properties** - Automatically creates required custom fields
- ✅ **Associations** - Links contacts to companies and deals to both
- ✅ **Progress tracking** - Real-time progress bars and status updates
- ✅ **Error handling** - Graceful handling of API errors with retry logic

## Data Mappings

### Companies ← Customers
- Standard fields: name, domain, city, state, country, phone, zip, address
- Custom fields: `erp_customer_number`, `credit_limit`, `sales_rep_employee_number`

### Contacts ← Customer Contacts
- Standard fields: firstname, lastname, email, company, phone, jobtitle
- Custom fields: `erp_customer_number`

### Deals ← Orders
- Standard fields: dealname, amount, dealstage, closedate, pipeline
- Custom fields: `erp_order_number`, `erp_customer_number`, `payment_status`

## Documentation

- [Project Overview](specs/PROJECT.md) - Purpose and architecture
- [HubSpot Setup](specs/setup/HUBSPOT.md) - Detailed setup instructions
- [Classic Models API](specs/api/CLASSIC-MODELS.md) - ERP API documentation
- [Architecture Guide](docs/architecture.md) - Technical architecture details
- [API Reference](docs/api-reference.md) - CLI command reference
- [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions

## Requirements

- Python 3.9 or higher
- HubSpot account (free tier supported)
- HubSpot API access token with required scopes

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
- 🔜 **Salesforce** - Coming soon
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