# Salesforce Integration - Plan Summary

## Executive Overview

This document provides a high-level summary of the plan to add Salesforce CRM support to the Classic Models Seeder CLI, following the same patterns established for HubSpot integration.

## Objectives

1. Enable seeding of Salesforce Developer Edition with Classic Models demo data
2. Support 122 Accounts, 23 Contacts, and 326 Opportunities
3. Implement idempotent operations using External ID fields
4. Maintain architectural consistency with HubSpot implementation
5. Provide comprehensive testing and documentation

## Key Deliverables

### 1. Specifications ✅
- **Setup Guide**: `specs/setup/SALESFORCE.md` (283 lines)
  - Account creation instructions
  - Connected App configuration
  - OAuth 2.0 setup
  - Data mappings and custom fields
  - CLI command reference

- **Implementation Plan**: `docs/salesforce-implementation-plan.md` (673 lines)
  - Detailed technical architecture
  - Component specifications
  - Timeline and effort estimates
  - Testing strategy
  - Risk assessment

### 2. Data Mappings

| Salesforce Object | Classic Models Source | Count | Key Fields |
|-------------------|----------------------|-------|------------|
| **Account** | Customers | 122 | Name, BillingAddress, Phone, ERP_Customer_Number__c |
| **Contact** | Employees | 23 | FirstName, LastName, Email, ERP_Employee_Number__c |
| **Opportunity** | Orders | 326 | Name, Amount, Stage, CloseDate, ERP_Order_Number__c |

### 3. Custom Fields

**Account** (3 fields):
- `ERP_Customer_Number__c` - External ID for idempotency
- `Credit_Limit__c` - Customer credit limit
- `Sales_Rep_Employee_Number__c` - Assigned sales rep

**Contact** (3 fields):
- `ERP_Employee_Number__c` - External ID for idempotency
- `Office_Code__c` - Office location
- `Reports_To_Employee_Number__c` - Manager reference

**Opportunity** (7 fields):
- `ERP_Order_Number__c` - External ID for idempotency
- `Order_Date__c`, `Required_Date__c`, `Shipped_Date__c` - Date tracking
- `Order_Status__c` - ERP status
- `Payment_Status__c` - Payment tracking
- `Order_Comments__c` - Order notes

### 4. Implementation Components

```
cmcli/
├── salesforce/
│   ├── auth.py           # OAuth 2.0 authentication (4h)
│   ├── client.py         # REST API client with rate limiting (8h)
│   ├── fields.py         # Custom field definitions (3h)
│   ├── transformers.py   # Data transformation layer (6h)
│   └── seeder.py         # Seeding orchestration (8h)
├── commands/
│   └── salesforce.py     # CLI commands (6h)
└── config.py             # Salesforce configuration (2h)
```

### 5. CLI Commands

| Command | Description |
|---------|-------------|
| `cmcli salesforce verify` | Verify credentials and permissions |
| `cmcli salesforce setup-fields` | Create custom fields |
| `cmcli salesforce seed` | Seed all data |
| `cmcli salesforce seed --accounts-only` | Seed only accounts |
| `cmcli salesforce seed --contacts-only` | Seed only contacts |
| `cmcli salesforce seed --opportunities-only` | Seed only opportunities |
| `cmcli salesforce purge` | Delete all seeded data |

## Technical Approach

### Authentication
- **OAuth 2.0 Username-Password Flow** for automation
- Connected App with Consumer Key/Secret
- Automatic token refresh on expiration
- Security token appended to password

### API Strategy
- **Salesforce REST API v59.0** (Winter '24)
- External ID upserts for idempotency
- Composite API for batch operations
- Rate limiting: 5,000 calls per 24 hours

### Seeding Order
1. **Accounts** → Create/update all customer accounts
2. **Contacts** → Create/update employees with account links
3. **Opportunities** → Create/update orders with account/contact links

### Idempotency
- Use External ID fields (`ERP_Customer_Number__c`, etc.)
- PATCH `/sobjects/{object}/{external_id_field}/{external_id}`
- Update existing records instead of creating duplicates

## Timeline & Resources

| Phase | Duration | Effort |
|-------|----------|--------|
| **Phase 1: Specifications** | Complete | 4h |
| **Phase 2: Implementation** | 1-2 weeks | 37h |
| **Phase 3: Testing** | 1 week | 24h |
| **Phase 4: Documentation** | 3-4 days | 10h |
| **Phase 5: Deployment** | 2-3 days | 9h |
| **Total** | **2-3 weeks** | **84h** |

*Assuming 1 developer working 40 hours/week*

## Testing Strategy

### Unit Tests (12h)
- Authentication flow
- API client methods
- Data transformations
- Seeding logic

### Integration Tests (8h)
- Full seeding workflow
- Partial seeding flags
- Idempotency verification
- Error recovery

### Manual Testing (4h)
- End-to-end user workflow
- Salesforce UI verification
- Edge case scenarios

**Target**: 90%+ code coverage

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| **Rate Limits** | Batch operations, Composite API, exponential backoff |
| **Token Expiration** | Automatic refresh, retry logic |
| **Field Conflicts** | Check existing fields before creation |
| **Data Errors** | Comprehensive validation, unit tests |

## Success Criteria

✅ All CLI commands functional and tested  
✅ Idempotent seeding (no duplicates on re-run)  
✅ 90%+ test coverage  
✅ Complete user and developer documentation  
✅ Consistent with HubSpot implementation patterns  
✅ Rate limiting handled gracefully  
✅ Clear, actionable error messages  

## Dependencies

### Required
- Salesforce Developer Edition account (free)
- Connected App with OAuth credentials
- Python packages: `requests`, `pydantic`, `click`, `rich`, `tenacity` (all installed)

### Optional
- `simple-salesforce` library (consider for helper functions)

## Comparison: HubSpot vs Salesforce

| Aspect | HubSpot | Salesforce |
|--------|---------|------------|
| **Authentication** | Service Key (API token) | OAuth 2.0 (Connected App) |
| **Objects** | Companies, Contacts, Deals | Accounts, Contacts, Opportunities |
| **Custom Fields** | Properties | Custom Fields |
| **External ID** | Custom property | External ID field type |
| **Rate Limit** | 100 req/10s | 5,000 req/24h |
| **API Version** | v3/v4 | REST API v59.0 |
| **Batch API** | Batch endpoints | Composite API |

## Next Steps

1. **Review & Approve Plan** - Stakeholder sign-off
2. **Set Up Dev Environment** - Create Salesforce Developer Edition account
3. **Begin Implementation** - Start with Phase 2 (auth.py, client.py)
4. **Iterative Development** - Build, test, document each component
5. **Integration Testing** - Test with real Salesforce org
6. **Documentation** - Complete user guides
7. **Code Review** - Ensure quality and consistency
8. **Release** - Merge to main, tag version v0.2.0

## Questions & Decisions

### Open Questions
- Should we use `simple-salesforce` library or pure `requests`?
- Do we need Bulk API support for large datasets?
- Should we support Salesforce Sandbox environments?

### Decisions Made
✅ Use OAuth 2.0 Username-Password flow (automation-friendly)  
✅ Use External ID fields for idempotency  
✅ Follow HubSpot implementation patterns  
✅ Target Salesforce REST API v59.0  
✅ Support Developer Edition (5,000 API calls/day)  

## References

- **Specifications**: `specs/setup/SALESFORCE.md`
- **Implementation Plan**: `docs/salesforce-implementation-plan.md`
- **HubSpot Reference**: `cmcli/hubspot/` (for patterns)
- **Salesforce Docs**: https://developer.salesforce.com/docs

---

**Document Status**: ✅ Complete  
**Last Updated**: 2026-03-23  
**Next Review**: Before implementation begins