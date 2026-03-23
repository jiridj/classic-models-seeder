# Classic Models API

## Overview

The Classic Models API is a RESTful API built on the Classic Models tutorial database, providing comprehensive access to a simulated ERP system for a collectible model products distributor.

**Version**: v4.3.0  
**Base Path**: `/classic-models`  
**Technology**: Django REST Framework with MySQL database  
**Authentication**: JWT (JSON Web Token)
## Source Code

The Classic Models API is open source and available on GitHub:
- **Repository**: https://github.com/jiridj/classic-models-api
- **License**: Open source

You can clone and host your own instance of the API for development, testing, or demonstration purposes. The repository includes:
- Complete Django application source code
- MySQL database schema and sample data
- Docker configuration for easy deployment
- Setup and installation instructions


## Purpose

This API serves as a demonstration ERP system for integration scenarios, supporting:
- Customer relationship management
- Product catalog management
- Order processing and fulfillment
- Payment tracking and reconciliation
- Employee and office management
- Sales representative assignment

## API Structure

### Authentication Endpoints (`/api/auth/`)

Manage user authentication and token lifecycle:
- **Login**: Obtain JWT access and refresh tokens
- **Logout**: Invalidate refresh tokens
- **Signup**: Register new users
- **Refresh**: Obtain new access tokens
- **Me**: Get current user information
- **Rate Limit Demo**: Test rate limiting functionality

### Data Endpoints (`/api/v1/`)

All data endpoints require JWT authentication and support standard REST operations (GET, POST, PUT, PATCH, DELETE where applicable).

#### Core Entities

1. **Product Lines** - Product categories and classifications
2. **Products** - Individual product catalog items with pricing and inventory
3. **Offices** - Company office locations
4. **Employees** - Sales representatives and staff with organizational hierarchy
5. **Customers** - Customer master data with credit limits and contact information
6. **Orders** - Sales orders with status tracking and fulfillment dates
7. **Order Details** - Line items for orders with product quantities and pricing
8. **Payments** - Payment transactions and reconciliation records

#### Relationship Endpoints

The API provides nested endpoints for accessing related data:
- Products by product line
- Order details by product
- Employees by office
- Customers by sales representative
- Employee reporting hierarchy
- Orders by customer
- Payments by customer
- Order details by order

## Key Features

### Security
- JWT-based authentication with access and refresh tokens
- Token expiration and refresh mechanisms
- Protected endpoints requiring valid authentication
- Rate limiting capabilities

### Data Operations
- Full CRUD operations on all entities
- Pagination support for list endpoints
- Filtering and querying capabilities
- Relationship traversal through nested endpoints

### Integration Patterns
- RESTful API design following industry standards
- JSON request/response format
- Standard HTTP status codes
- Comprehensive error handling

## Demo Credentials

For testing and demonstration purposes:
- **Username**: `demo`
- **Password**: `demo123`

## API Documentation

For detailed endpoint specifications, request/response schemas, and interactive testing, refer to the complete OpenAPI specification:
- **File**: `specs/apis/classic-models-4.3.0.yaml`
- **Format**: OpenAPI 3.0.3

## Use Cases

This API supports the following integration scenarios:
1. **Lead-to-Customer**: Create customers from CRM lead data
2. **Order Creation**: Generate orders from closed sales opportunities
3. **Payment Reconciliation**: Record and track payment transactions
4. **Customer 360**: Retrieve comprehensive customer data including orders and payments
5. **Inventory Management**: Access product catalog and availability
6. **Sales Analytics**: Query order history and payment data