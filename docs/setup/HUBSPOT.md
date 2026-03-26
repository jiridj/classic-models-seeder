# HubSpot CRM Setup

## Overview

This guide covers setting up a free HubSpot CRM account and configuring it for the Classic Models demo. The `cmcli` tool handles all data seeding and property setup automatically.

## Step 1: Create a Free HubSpot Account

1. Go to [HubSpot's signup page](https://www.hubspot.com/products/get-started)
2. Click **"Get started free"** and complete registration
3. Verify your email and complete the onboarding wizard

## Step 2: Create API Access Credentials

### Option A: Service Keys (Recommended)

1. Log in to [app.hubspot.com](https://app.hubspot.com)
2. Go to **Settings** → **Integrations** → **Service Keys**
3. Click **"Create service key"**
4. Configure:
   - **Name**: `Classic Models Integration`
   - **Description**: `Integration for Classic Models demo workflows`
5. Select **Scopes**:
   - `crm.objects.contacts.read` / `crm.objects.contacts.write`
   - `crm.objects.companies.read` / `crm.objects.companies.write`
   - `crm.objects.deals.read` / `crm.objects.deals.write`
   - `crm.objects.products.read` / `crm.objects.products.write`
   - `crm.objects.line_items.read` / `crm.objects.line_items.write`
   - `crm.schemas.contacts.read` / `crm.schemas.contacts.write`
   - `crm.schemas.companies.read` / `crm.schemas.companies.write`
   - `crm.schemas.deals.read` / `crm.schemas.deals.write`
   - `crm.schemas.line_items.read`
   - `crm.objects.owners.read` (optional)
   - `timeline` (optional)
6. Click **"Create"** and **copy the key immediately** — it's only shown once

> **Note**: Tickets are not included — support tickets are managed in Trello for this demo.

### Option B: Legacy Apps

If Service Keys are not available:

1. Go to **Settings** → **Integrations** → **Legacy Apps**
2. Click **"Create legacy app"** with the same name, description, and scopes as above
3. Copy the Access Token immediately

## Step 3: Find Your HubSpot Account ID

- **From URL**: The number in `https://app.hubspot.com/contacts/12345678/` is your Account ID
- **From Settings**: Settings → Account Management → Account Details → Hub ID
- **From Menu**: Click your avatar top-right → Account ID shown below your name

## Step 4: Configure the CLI

Add credentials to `.env` in the project root:

```bash
HUBSPOT_ACCESS_TOKEN=pat-na1-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
HUBSPOT_ACCOUNT_ID=12345678
```

## Step 5: Run Setup

```bash
# Verify access and permissions
cmcli verify hubspot

# Create custom properties in HubSpot
cmcli setup-properties hubspot

# Seed all demo data
cmcli seed hubspot
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `cmcli hubspot verify` | Verify API credentials and check read/write permissions |
| `cmcli hubspot seed` | Seed all data (companies, contacts, products, deals, line items) |
| `cmcli hubspot seed --companies-only` | Seed only companies |
| `cmcli hubspot seed --contacts-only` | Seed only contacts (requires companies) |
| `cmcli hubspot seed --products-only` | Seed only products |
| `cmcli hubspot seed --deals-only` | Seed only deals (requires companies and contacts) |
| `cmcli hubspot seed --line-items-only` | Seed only line items (requires products and deals) |

## Data Seeded

The `cmcli hubspot seed` command seeds the full Classic Models dataset:

| HubSpot Object | Source | Count |
|----------------|--------|-------|
| Companies | Classic Models customers | 122 |
| Contacts | Classic Models customer contacts | 122 |
| Products | Classic Models products | 110 |
| Deals | Classic Models orders | 326 |
| Line Items | Order details | 2,996 |

Seeding is **idempotent** — re-running updates existing records (except line items which are created fresh each time).

## Data Mappings

### Companies ← Customers

| HubSpot Property | Classic Models Field | Notes |
|------------------|---------------------|-------|
| `name` | `customerName` | |
| `domain` | Generated from name | Lowercase, hyphenated |
| `city` | `city` | |
| `state` | `state` | |
| `country` | `country` | |
| `phone` | `phone` | |
| `zip` | `postalCode` | |
| `address` | `addressLine1` | |
| `erp_customer_number` | `customerNumber` | Custom property |
| `credit_limit` | `creditLimit` | Custom property |
| `sales_rep_employee_number` | `salesRepEmployeeNumber` | Custom property |

### Contacts ← Customer Contacts

| HubSpot Property | Classic Models Field | Notes |
|------------------|---------------------|-------|
| `firstname` | `contactFirstName` | |
| `lastname` | `contactLastName` | |
| `email` | Generated | `firstname.lastname@domain` |
| `company` | `customerName` | Required for list view display |
| `phone` | `phone` | |
| `jobtitle` | — | Hardcoded: "Purchasing Manager" |
| `erp_customer_number` | `customerNumber` | Custom property |

### Deals ← Orders

| HubSpot Property | Classic Models Field | Notes |
|------------------|---------------------|-------|
| `dealname` | Generated | `Order {N} - {customerName}` |
| `amount` | Sum of order details | `quantityOrdered × priceEach` |
| `dealstage` | Mapped from `status` | See table below |
| `closedate` | `shippedDate` or `orderDate` | |
| `pipeline` | — | `default` |
| `erp_order_number` | `orderNumber` | Custom property |
| `erp_customer_number` | `customerNumber` | Custom property |
| `payment_status` | Derived from payments | Custom property |

**Order status → Deal stage mapping**:

| Classic Models Status | HubSpot Deal Stage |
|----------------------|-------------------|
| Shipped | Closed Won |
| Resolved | Closed Won |
| Cancelled | Closed Lost |
| On Hold | Contract Sent |
| Disputed | Contract Sent |
| In Process | Presentation Scheduled |

## Custom Properties Created

### Companies
- `erp_customer_number` (text) — Classic Models customer number
- `credit_limit` (number) — Customer credit limit from ERP
- `sales_rep_employee_number` (text) — Assigned sales rep employee number

### Contacts
- `erp_customer_number` (text) — Associated customer number

### Products
- `erp_product_code` (text) — Product code from Classic Models ERP
- `product_line` (text) — Product line category (e.g., "Classic Cars", "Motorcycles")
- `product_scale` (text) — Scale of the model (e.g., "1:10", "1:24")
- `product_vendor` (text) — Vendor/manufacturer of the product
- `quantity_in_stock` (number) — Current inventory quantity
- `buy_price` (number) — Wholesale/buy price
- `msrp` (number) — Manufacturer's Suggested Retail Price

### Deals
- `erp_order_number` (text) — Classic Models order number
- `erp_customer_number` (text) — Customer reference
- `payment_status` (dropdown) — `pending` / `paid` / `partial` / `overdue`
- `payment_link` (text) — Stripe payment link URL

### Line Items
Line items use standard HubSpot properties (`quantity`, `price`, `name`) and are associated with both deals and products.

## webMethods Connector Configuration

| Parameter | Value |
|-----------|-------|
| Authentication Type | Service Key or Legacy App Token |
| Access Token | `{YOUR_SERVICE_KEY_OR_TOKEN}` |
| Account ID | Your Hub ID |

## Rate Limits (Free Tier)

- 100 requests per 10 seconds
- The CLI includes automatic retry with backoff for 429 responses

## Additional Resources

- [HubSpot API Documentation](https://developers.hubspot.com/docs/api/overview)
- [Service Keys Documentation](https://developers.hubspot.com/docs/api/service-keys)
- [CRM API Reference](https://developers.hubspot.com/docs/api/crm/understanding-the-crm)
- [webMethods HubSpot Connector](https://www.ibm.com/docs/en/wm-integration-ipaas?topic=marketing-hubspot)
