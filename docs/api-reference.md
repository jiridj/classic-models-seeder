# API Reference

Complete reference for all `cmcli` commands and options.

## Global Options

Available for all commands:

```bash
cmcli [OPTIONS] COMMAND [ARGS]...
```

### Options

- `--version` - Show version and exit
- `--verbose, -v` - Enable verbose output (DEBUG level logging)
- `--quiet, -q` - Suppress all output except errors
- `--help` - Show help message and exit

## Commands

### `cmcli update`

Update timestamps in the Classic Models dataset to current dates.

```bash
cmcli update
```

**Description**: Updates all date fields in SQL and JSON data files to make the demo data current. Historical orders (Shipped, Resolved, Disputed, Cancelled) are mapped to the last 18 months, and future orders (In Process, On Hold) to the next 3 months.

**Arguments**: None

**Options**: None

**Examples**:
```bash
# Update timestamps
cmcli update

# Update with verbose output
cmcli --verbose update
```

**Output**:
- Progress information
- Backup file locations
- Validation results
- Summary of changes

---

### `cmcli hubspot`

HubSpot CRM command group.

```bash
cmcli hubspot COMMAND [OPTIONS]
```

**Subcommands**:
- `verify` - Verify API credentials and permissions
- `seed` - Seed HubSpot with Classic Models data

---

### `cmcli hubspot verify`

Verify HubSpot API credentials and permissions.

```bash
cmcli hubspot verify
```

**Description**: Checks that your HubSpot API credentials are valid and that you have the required permissions to seed data.

**Checks Performed**:
1. Authentication validity
2. Read permissions for companies, contacts, deals
3. Write permissions for companies, contacts, deals
4. Schema access for custom properties

**Arguments**: None

**Options**: None

**Examples**:
```bash
# Verify credentials
cmcli hubspot verify

# Verify with detailed output
cmcli --verbose hubspot verify
```

**Exit Codes**:
- `0` - All checks passed
- `1` - Authentication failed or missing permissions

**Output**:
```
✓ Testing authentication...
  ✓ Authentication successful

✓ Checking read permissions...
  ✓ Can read companies
  ✓ Can read contacts
  ✓ Can read deals

✓ Checking write permissions...
  ✓ Can access companies schema
  ✓ Can access contacts schema
  ✓ Can access deals schema

✓ All checks passed! Ready to seed HubSpot.
```

---

### `cmcli hubspot seed`

Seed HubSpot CRM with Classic Models data.

```bash
cmcli hubspot seed [OPTIONS]
```

**Description**: Seeds HubSpot with companies (from customers), contacts (from customer contacts), and deals (from orders). The process is idempotent - running multiple times will update existing records rather than creating duplicates.

**Options**:
- `--companies-only` - Seed only companies (customers)
- `--contacts-only` - Seed only contacts (requires companies to exist)
- `--deals-only` - Seed only deals (requires companies and contacts to exist)

**Arguments**: None

**Examples**:
```bash
# Seed all data
cmcli hubspot seed

# Seed only companies
cmcli hubspot seed --companies-only

# Seed only contacts
cmcli hubspot seed --contacts-only

# Seed only deals
cmcli hubspot seed --deals-only

# Seed with verbose logging
cmcli --verbose hubspot seed
```

**Data Seeded**:
- **Companies**: 122 records from Classic Models customers
- **Contacts**: 122 records from customer contact information
- **Deals**: 326 records from Classic Models orders

**Process**:
1. Check/create custom properties
2. Load data from JSON files
3. Transform data to HubSpot format
4. Search for existing records by ERP ID
5. Create new or update existing records
6. Create associations between objects

**Exit Codes**:
- `0` - Seeding completed successfully
- `1` - Configuration error, authentication error, or seeding failed

**Output**:
```
Starting HubSpot seeding...
Account ID: 12345678

Checking custom properties...
  ✓ Created companies.erp_customer_number
  ✓ All custom properties ready

Seeding 122 companies...
Processing companies... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
✓ Companies: 122 created, 0 updated, 0 skipped

Seeding 122 contacts...
Processing contacts... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
✓ Contacts: 122 created, 0 updated, 0 skipped

Seeding 326 deals...
Processing deals... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
✓ Deals: 326 created, 0 updated, 0 skipped

✓ Seeding completed successfully!

┏━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Object Type ┃ Records ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━┩
│ Companies   │     122 │
│ Contacts    │     122 │
│ Deals       │     326 │
└─────────────┴─────────┘
```

---

## Environment Variables

Required environment variables (set in `.env` file):

### HubSpot Configuration

```bash
# HubSpot API access token (Service Key or Legacy App token)
HUBSPOT_ACCESS_TOKEN=pat-na1-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# HubSpot account ID (Hub ID)
HUBSPOT_ACCOUNT_ID=12345678
```

### Classic Models API (Optional)

```bash
# Classic Models API base URL
CLASSIC_MODELS_API_URL=http://localhost:8000/classic-models

# API credentials
CLASSIC_MODELS_USERNAME=demo
CLASSIC_MODELS_PASSWORD=demo123
```

---

## Error Handling

### Configuration Errors

**Error**: `HUBSPOT_ACCESS_TOKEN not found in environment`

**Solution**: Create a `.env` file with your HubSpot credentials. See [HubSpot Setup Guide](../specs/setup/HUBSPOT.md).

### Authentication Errors

**Error**: `Authentication failed. Check your access token.`

**Solution**: 
1. Verify your access token is correct
2. Check that the token hasn't expired
3. Run `cmcli hubspot verify` to diagnose

### Permission Errors

**Error**: `Permission denied. Check your API scopes and permissions.`

**Solution**: Ensure your API key has the following scopes:
- `crm.objects.contacts.read` / `write`
- `crm.objects.companies.read` / `write`
- `crm.objects.deals.read` / `write`
- `crm.schemas.contacts.read` / `write`
- `crm.schemas.companies.read` / `write`
- `crm.schemas.deals.read` / `write`

### Rate Limit Errors

**Error**: `Rate limit exceeded`

**Solution**: The CLI automatically handles rate limiting with retry logic. If you see this error repeatedly, wait a few minutes and try again.

### Data File Errors

**Error**: `Data file not found: data/json/customers.json`

**Solution**: Ensure you're running the command from the project root directory and that all data files exist in `data/json/`.

---

## Logging

### Log Levels

- **ERROR** (default with `--quiet`): Only critical errors
- **INFO** (default): Normal operation messages
- **DEBUG** (with `--verbose`): Detailed diagnostic information

### Log Output

Logs are written to stderr using the Rich library for formatted output.

**Example with verbose logging**:
```bash
cmcli --verbose hubspot seed
```

**Output includes**:
- API request/response details
- Transformation logic
- Rate limiting information
- Retry attempts
- Full stack traces on errors

---

## Exit Codes

- `0` - Success
- `1` - Error (configuration, authentication, API, or data error)

---

## Tips

### Idempotent Operations

All seeding operations are idempotent. You can safely run `cmcli hubspot seed` multiple times:
- Existing records are updated, not duplicated
- Records are matched by ERP ID (customer number, order number)
- Associations are preserved

### Partial Seeding

Use flags to seed specific object types:
```bash
# Seed companies first
cmcli hubspot seed --companies-only

# Then contacts (requires companies)
cmcli hubspot seed --contacts-only

# Finally deals (requires companies and contacts)
cmcli hubspot seed --deals-only
```

### Debugging

Enable verbose logging to see detailed information:
```bash
cmcli --verbose hubspot seed
```

### Performance

- Seeding 122 companies: ~2-3 minutes
- Seeding 122 contacts: ~2-3 minutes
- Seeding 326 deals: ~5-7 minutes
- Total time: ~10-15 minutes (with rate limiting)

Times may vary based on API response times and rate limits.