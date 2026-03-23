# Classic Models Seeder

## What is the purpose of this project?

Many integration demos require pre-populated applications that all work with the same dataset. You need the same data across multiple applications to effectively showcase how integration and APIs helps automate workflows and provide data consistency. This project focuses on the Classic Models demo dataset and offers a python-based CLI for populating different applications based on that dataset.

## Classic Models ERP

We've used the Classic Models dataset from old MySQL tutorials to create a [custom ERP system](/specs/api/CLASSIC-MODELS.md) with an OpenAPI compliant REST API. This ERP is the centerpiece in all demo scenarios. The CLI provided by this project will provide seeding and updating datasets in other apps to keep them in sync with the Classic Models ERP data.  

## Command-Line Interface

The CLI is called `cmcli` and enables seeding or updating one application at a time. 

For each application it offers two commands: `verify` and `seed`. `Verify` checks that all required credentials and permissions are available to seed the application. `Seed` actually seeds it. The structure of the CLI commands is `cmcli <app-name> <command-name>`.

The root command `update` updates the timestamps in the dataset to have current data and related timestamps in the Classic Models ERP and demo applications. 

Examples:
- `cmcli update` to update the timestamps in the seed dataset. 
- `cmcli hubspot verify` to verify Hubspot access. 
- `cmcli hubspot seed` to upsert data into Hubspot for synchronization.

## Supported Applications

- [Hubspot CRM](/specs/setup/HUBSPOT.md)