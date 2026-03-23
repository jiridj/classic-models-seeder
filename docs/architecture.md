# Architecture Guide

## Overview

The Classic Models Seeder is built as a modular Python CLI application using the Click framework. It follows a layered architecture with clear separation of concerns.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI Layer                            │
│  (cmcli/cli.py, cmcli/commands/)                            │
│  - Command parsing and validation                            │
│  - User interaction and output formatting                    │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                    Application Layer                         │
│  (cmcli/hubspot/seeder.py)                                  │
│  - Orchestration logic                                       │
│  - Business rules and workflows                              │
│  - Progress tracking                                         │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
┌───────▼──────┐ ┌──▼──────┐ ┌──▼────────────┐
│ Transformation│ │ API     │ │ Data Loading  │
│ Layer         │ │ Client  │ │ Layer         │
│ (transformers)│ │ (client)│ │ (loader)      │
└───────────────┘ └─────────┘ └───────────────┘
```

## Component Details

### CLI Layer

**Location**: `cmcli/cli.py`, `cmcli/commands/`

**Responsibilities**:
- Parse command-line arguments and options
- Validate user input
- Display formatted output using Rich library
- Handle user errors gracefully

**Key Components**:
- `cli.py`: Main entry point, global options
- `commands/update.py`: Timestamp update command
- `commands/hubspot.py`: HubSpot command group (verify, seed)

### Configuration Management

**Location**: `cmcli/config.py`

**Responsibilities**:
- Load environment variables from `.env` file
- Validate required configuration
- Provide typed configuration objects
- Manage paths to data files

**Key Classes**:
- `Config`: Main configuration manager
- `HubSpotConfig`: HubSpot-specific configuration
- `ClassicModelsConfig`: Classic Models API configuration

### Data Loading Layer

**Location**: `cmcli/data/loader.py`

**Responsibilities**:
- Load JSON data files
- Provide typed access to dataset
- Handle file I/O errors

**Key Classes**:
- `DataLoader`: Loads Classic Models data from JSON files

### Transformation Layer

**Location**: `cmcli/hubspot/transformers.py`

**Responsibilities**:
- Transform Classic Models data to HubSpot format
- Apply field mappings
- Generate synthetic data (emails, domains)
- Calculate derived values (order totals, payment status)

**Key Classes**:
- `HubSpotTransformer`: Main transformation logic
- Helper functions for domain/email generation

### API Client Layer

**Location**: `cmcli/hubspot/client.py`

**Responsibilities**:
- Communicate with HubSpot API
- Handle authentication
- Implement rate limiting
- Retry failed requests
- Provide typed API methods

**Key Classes**:
- `HubSpotClient`: Main API client
- `HubSpotAPIError`: Base exception class
- `HubSpotAuthError`: Authentication errors
- `HubSpotRateLimitError`: Rate limit errors

**Features**:
- Token bucket rate limiter (100 req/10s)
- Exponential backoff retry logic
- Automatic 429 handling
- Batch operations support

### Application Layer

**Location**: `cmcli/hubspot/seeder.py`

**Responsibilities**:
- Orchestrate seeding workflow
- Manage dependencies (companies → contacts → deals)
- Track created objects for associations
- Implement idempotent upserts
- Display progress

**Key Classes**:
- `HubSpotSeeder`: Main orchestration logic

**Workflow**:
1. Ensure custom properties exist
2. Seed companies (check for existing by ERP ID)
3. Seed contacts (associate with companies)
4. Seed deals (associate with companies and contacts)

### Utilities

**Location**: `cmcli/utils/`

**Components**:
- `logging.py`: Logging configuration with Rich handler
- `retry.py`: Retry decorators and rate limiter

## Data Flow

### Seeding Flow

```
User Command
    │
    ├─> Load Configuration (.env)
    │
    ├─> Initialize API Client
    │
    ├─> Load Data Files (JSON)
    │
    ├─> Transform Data
    │   ├─> Customers → Companies
    │   ├─> Customers → Contacts
    │   └─> Orders → Deals
    │
    ├─> Check for Existing Records (by ERP ID)
    │
    ├─> Upsert to HubSpot
    │   ├─> Create if new
    │   └─> Update if exists
    │
    └─> Create Associations
        ├─> Contact → Company
        ├─> Deal → Company
        └─> Deal → Contact
```

### Error Handling Flow

```
API Request
    │
    ├─> Rate Limiter (wait if needed)
    │
    ├─> Make HTTP Request
    │
    ├─> Handle Response
    │   ├─> 200-299: Success
    │   ├─> 401/403: Auth Error (fail immediately)
    │   ├─> 429: Rate Limit (retry with backoff)
    │   └─> Other: Retry with exponential backoff
    │
    └─> Return Result or Raise Exception
```

## Design Patterns

### Dependency Injection
- Configuration and clients passed to components
- Enables testing with mocks

### Repository Pattern
- `DataLoader` abstracts data access
- Easy to swap JSON for API or database

### Strategy Pattern
- `HubSpotTransformer` encapsulates transformation logic
- Can add transformers for other platforms

### Decorator Pattern
- `@retry_with_backoff` for automatic retries
- Separates retry logic from business logic

## Extension Points

### Adding New Applications

1. Create new module: `cmcli/<app>/`
2. Implement client: `cmcli/<app>/client.py`
3. Implement transformer: `cmcli/<app>/transformers.py`
4. Implement seeder: `cmcli/<app>/seeder.py`
5. Add command group: `cmcli/commands/<app>.py`
6. Register in `cmcli/cli.py`

### Adding New Data Sources

1. Extend `DataLoader` or create new loader
2. Update transformers to handle new data format
3. Update configuration if needed

## Performance Considerations

### Rate Limiting
- Token bucket algorithm prevents API throttling
- Configurable rate (default: 100 req/10s for HubSpot free tier)

### Batch Operations
- Use HubSpot batch APIs where available (up to 100 records)
- Reduces API calls and improves performance

### Idempotency
- Search by ERP ID before creating
- Update existing records instead of duplicating
- Safe to run multiple times

## Security

### Credentials
- Stored in `.env` file (not committed to git)
- Loaded via python-dotenv
- Never logged or displayed

### API Access
- Uses HubSpot Service Keys or Legacy Apps
- Requires explicit scopes
- Token-based authentication

## Testing Strategy

### Unit Tests
- Test transformers with sample data
- Test utility functions
- Mock API responses

### Integration Tests
- Test API client with mock server
- Test end-to-end workflows

### Manual Testing
- Verify command with real credentials
- Seed command with test account