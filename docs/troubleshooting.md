# Troubleshooting Guide

Common issues and solutions for the Classic Models Seeder CLI.

## Installation Issues

### Issue: `pip install -e .` fails

**Symptoms**:
```
ERROR: Could not find a version that satisfies the requirement click>=8.1.0
```

**Solutions**:
1. Upgrade pip: `pip install --upgrade pip`
2. Check Python version: `python --version` (requires 3.9+)
3. Try installing dependencies first: `pip install -r requirements.txt`

### Issue: Command not found after installation

**Symptoms**:
```bash
$ cmcli
bash: cmcli: command not found
```

**Solutions**:
1. Ensure you installed with `-e` flag: `pip install -e .`
2. Check if pip bin directory is in PATH
3. Try running directly: `python -m cmcli.cli`
4. Reinstall: `pip uninstall classic-models-seeder && pip install -e .`

---

## Configuration Issues

### Issue: Environment variables not loaded

**Symptoms**:
```
Configuration error: HUBSPOT_ACCESS_TOKEN not found in environment
```

**Solutions**:
1. Create `.env` file in project root (not in subdirectory)
2. Verify file is named exactly `.env` (not `.env.txt`)
3. Check file contents match format:
   ```
   HUBSPOT_ACCESS_TOKEN=pat-na1-...
   HUBSPOT_ACCOUNT_ID=12345678
   ```
4. Ensure no spaces around `=` sign
5. Run from project root directory

### Issue: Invalid access token format

**Symptoms**:
```
Authentication failed. Check your access token.
```

**Solutions**:
1. Verify token format: Should start with `pat-na1-` or similar
2. Check for extra spaces or quotes in `.env` file
3. Regenerate token in HubSpot settings
4. Ensure token hasn't expired

---

## Authentication Issues

### Issue: 401 Unauthorized

**Symptoms**:
```
Authentication failed. Check your access token.
```

**Solutions**:
1. Verify access token is correct
2. Check token hasn't been revoked
3. Regenerate token in HubSpot:
   - Settings → Integrations → Service Keys
   - Create new service key
4. Update `.env` file with new token

### Issue: 403 Forbidden

**Symptoms**:
```
Permission denied. Check your API scopes and permissions.
```

**Solutions**:
1. Run `cmcli hubspot verify` to see which permissions are missing
2. Update API key scopes in HubSpot:
   - Settings → Integrations → Service Keys
   - Edit your service key
   - Add required scopes:
     - `crm.objects.contacts.read` / `write`
     - `crm.objects.companies.read` / `write`
     - `crm.objects.deals.read` / `write`
     - `crm.schemas.contacts.read` / `write`
     - `crm.schemas.companies.read` / `write`
     - `crm.schemas.deals.read` / `write`
3. Save and use the new token

---

## Rate Limiting Issues

### Issue: Rate limit exceeded repeatedly

**Symptoms**:
```
Rate limit exceeded, waiting 10s...
Rate limit exceeded, waiting 10s...
```

**Solutions**:
1. Wait a few minutes before retrying
2. The CLI automatically handles rate limiting - let it run
3. If on free tier, consider upgrading for higher limits
4. Avoid running multiple instances simultaneously

### Issue: Seeding takes too long

**Symptoms**:
- Process seems stuck
- Very slow progress

**Solutions**:
1. This is normal - rate limiting slows the process
2. Expected times:
   - 122 companies: 2-3 minutes
   - 122 contacts: 2-3 minutes
   - 326 deals: 5-7 minutes
3. Use `--verbose` to see detailed progress
4. Consider partial seeding with flags if you only need specific data

---

## Data Issues

### Issue: Data files not found

**Symptoms**:
```
Data file not found: data/json/customers.json
```

**Solutions**:
1. Ensure you're in the project root directory
2. Verify data files exist:
   ```bash
   ls data/json/
   # Should show: customers.json, orders.json, orderdetails.json, payments.json
   ```
3. If files are missing, restore from backup or re-clone repository

### Issue: Invalid JSON in data files

**Symptoms**:
```
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**Solutions**:
1. Check if data files were corrupted
2. Restore from `.backup` files if available
3. Re-clone repository to get fresh data files
4. Validate JSON: `python -m json.tool data/json/customers.json`

---

## Seeding Issues

### Issue: Duplicate records created

**Symptoms**:
- Multiple companies with same name
- Duplicate contacts or deals

**Solutions**:
1. This shouldn't happen - seeding is idempotent
2. Check if custom properties exist:
   ```bash
   cmcli hubspot verify
   ```
3. If properties are missing, they'll be created on next run
4. Delete duplicates manually in HubSpot
5. Re-run seed command - it will update existing records

### Issue: Associations not created

**Symptoms**:
- Contacts not linked to companies
- Deals not linked to contacts/companies

**Solutions**:
1. Ensure you seed in order:
   ```bash
   cmcli hubspot seed --companies-only
   cmcli hubspot seed --contacts-only
   cmcli hubspot seed --deals-only
   ```
2. Or use full seed: `cmcli hubspot seed` (handles order automatically)
3. Check HubSpot permissions include association creation
4. Re-run seed to create missing associations

### Issue: Some records skipped

**Symptoms**:
```
✓ Companies: 100 created, 0 updated, 22 skipped
```

**Solutions**:
1. Check logs with `--verbose` to see why records were skipped
2. Common reasons:
   - Invalid data format
   - Missing required fields
   - API errors for specific records
3. Review skipped records in logs
4. Fix data issues and re-run

---

## Custom Property Issues

### Issue: Cannot create custom properties

**Symptoms**:
```
Failed to create property erp_customer_number
```

**Solutions**:
1. Check schema write permissions:
   - `crm.schemas.companies.write`
   - `crm.schemas.contacts.write`
   - `crm.schemas.deals.write`
2. Verify property doesn't already exist with different type
3. Check HubSpot property limits (varies by tier)
4. Try creating property manually in HubSpot UI first

### Issue: Property type mismatch

**Symptoms**:
```
Property type mismatch: expected string, got number
```

**Solutions**:
1. Delete existing property in HubSpot
2. Re-run seed to create with correct type
3. Or update transformer to match existing property type

---

## Performance Issues

### Issue: High memory usage

**Symptoms**:
- Process uses excessive RAM
- System becomes slow

**Solutions**:
1. This is normal for large datasets
2. Close other applications
3. Consider processing in batches using flags:
   ```bash
   cmcli hubspot seed --companies-only
   # Wait, then:
   cmcli hubspot seed --contacts-only
   # Wait, then:
   cmcli hubspot seed --deals-only
   ```

### Issue: Network timeouts

**Symptoms**:
```
Request failed: Connection timeout
```

**Solutions**:
1. Check internet connection
2. Verify HubSpot API is accessible
3. Try again - CLI has automatic retry logic
4. If persistent, check firewall/proxy settings

---

## Debugging Tips

### Enable Verbose Logging

```bash
cmcli --verbose hubspot seed
```

Shows:
- API requests and responses
- Transformation details
- Rate limiting info
- Full error stack traces

### Check HubSpot API Status

Visit: https://status.hubspot.com/

### Test with Verify Command

```bash
cmcli hubspot verify
```

Diagnoses:
- Authentication issues
- Permission problems
- API connectivity

### Inspect Data Files

```bash
# View first customer
python -c "import json; print(json.load(open('data/json/customers.json'))[0])"

# Count records
python -c "import json; print(len(json.load(open('data/json/customers.json'))))"
```

### Check Environment

```bash
# Verify Python version
python --version  # Should be 3.9+

# Check installed packages
pip list | grep -E "click|requests|rich|pydantic"

# Test imports
python -c "import cmcli; print(cmcli.__version__)"
```

---

## Getting Help

If you're still experiencing issues:

1. **Check Documentation**:
   - [README.md](../README.md)
   - [Architecture Guide](architecture.md)
   - [API Reference](api-reference.md)
   - [HubSpot Setup](../specs/setup/HUBSPOT.md)

2. **Search Issues**:
   - GitHub Issues: https://github.com/jiridj/classic-models-seeder/issues
   - Look for similar problems

3. **Create an Issue**:
   - Include error messages
   - Provide steps to reproduce
   - Share relevant logs (with `--verbose`)
   - Mention your environment (OS, Python version)

4. **Community Support**:
   - GitHub Discussions: https://github.com/jiridj/classic-models-seeder/discussions

---

## Common Error Messages

### `ModuleNotFoundError: No module named 'cmcli'`

**Solution**: Install the package: `pip install -e .`

### `FileNotFoundError: [Errno 2] No such file or directory: '.env'`

**Solution**: Create `.env` file in project root with required variables

### `ValidationError: 1 validation error for HubSpotConfig`

**Solution**: Check `.env` file format and ensure all required variables are set

### `JSONDecodeError: Extra data`

**Solution**: Check JSON files for syntax errors, restore from backup if needed

### `ConnectionError: Max retries exceeded`

**Solution**: Check internet connection and HubSpot API status

---

## Best Practices

1. **Always run verify first**:
   ```bash
   cmcli hubspot verify
   ```

2. **Use version control for .env**:
   - Never commit `.env` to git
   - Use `.env.example` as template

3. **Backup before seeding**:
   - Export HubSpot data before first run
   - Keep backups of data files

4. **Test with small dataset first**:
   - Modify data files to include fewer records
   - Test full workflow
   - Then use complete dataset

5. **Monitor rate limits**:
   - Be patient with free tier
   - Consider upgrading for production use

6. **Keep logs**:
   - Save output of verbose runs
   - Helps diagnose issues later