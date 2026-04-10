"""API updater for pushing timestamp updates to Classic Models API."""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

import click

from cmcli.api.client import ClassicModelsClient, ClassicModelsAPIError
from cmcli.config import ClassicModelsConfig

logger = logging.getLogger(__name__)


class APIUpdater:
    """Updates Classic Models API with transformed data from JSON files."""
    
    def __init__(self, client: ClassicModelsClient, json_dir: Path):
        """Initialize API updater.
        
        Args:
            client: Classic Models API client
            json_dir: Directory containing JSON data files
        """
        self.client = client
        self.json_dir = json_dir
        self.stats = {
            "orders_updated": 0,
            "orders_failed": 0,
            "payments_updated": 0,
            "payments_failed": 0,
        }
    
    def load_json_data(self, filename: str) -> List[Dict[str, Any]]:
        """Load data from JSON file.
        
        Args:
            filename: Name of JSON file (e.g., 'orders.json')
        
        Returns:
            List of records from JSON file
        
        Raises:
            FileNotFoundError: If JSON file doesn't exist
        """
        filepath = self.json_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(
                f"JSON file not found: {filepath}\n"
                f"Please run 'cmcli update' first to generate JSON files."
            )
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def update_orders(self, dry_run: bool = False) -> int:
        """Update orders in the API with data from JSON file.
        
        Args:
            dry_run: If True, only show what would be updated without making changes
        
        Returns:
            Number of orders successfully updated
        """
        logger.info("Loading orders from JSON file...")
        orders = self.load_json_data("orders.json")
        total = len(orders)
        
        logger.info(f"Found {total} orders to update")
        
        if dry_run:
            logger.info("DRY RUN: No changes will be made")
            # Show sample of what would be updated
            if orders:
                sample = orders[0]
                logger.info(f"Sample order update:")
                logger.info(f"  Order Number: {sample.get('orderNumber')}")
                logger.info(f"  Order Date: {sample.get('orderDate')}")
                logger.info(f"  Required Date: {sample.get('requiredDate')}")
                logger.info(f"  Shipped Date: {sample.get('shippedDate')}")
                logger.info(f"  Status: {sample.get('status')}")
            return 0
        
        # Update orders with progress bar
        with click.progressbar(
            orders,
            label="Updating orders",
            length=total,
            show_pos=True,
        ) as bar:
            for order in bar:
                order_number = None
                try:
                    order_number = order.get("orderNumber")
                    if not order_number:
                        logger.warning("Order missing orderNumber, skipping")
                        self.stats["orders_failed"] += 1
                        continue
                    
                    # Prepare update data (only date fields)
                    # Note: API expects lowercase field names
                    update_data = {
                        "orderdate": order.get("orderDate"),
                        "requireddate": order.get("requiredDate"),
                        "shippeddate": order.get("shippedDate"),
                    }
                    
                    # Update via API
                    self.client.update_order(order_number, update_data)
                    self.stats["orders_updated"] += 1
                    
                except ClassicModelsAPIError as e:
                    logger.error(f"Failed to update order {order_number or 'unknown'}: {e}")
                    self.stats["orders_failed"] += 1
                except Exception as e:
                    logger.error(f"Unexpected error updating order {order_number or 'unknown'}: {e}")
                    self.stats["orders_failed"] += 1
        
        return self.stats["orders_updated"]
    
    def update_payments(self, dry_run: bool = False) -> int:
        """Update payments in the API with data from JSON file.
        
        Args:
            dry_run: If True, only show what would be updated without making changes
        
        Returns:
            Number of payments successfully updated
        """
        logger.info("Loading payments from JSON file...")
        payments = self.load_json_data("payments.json")
        total = len(payments)
        
        logger.info(f"Found {total} payments to update")
        
        if dry_run:
            logger.info("DRY RUN: No changes will be made")
            # Show sample of what would be updated
            if payments:
                sample = payments[0]
                logger.info(f"Sample payment update:")
                logger.info(f"  Customer Number: {sample.get('customerNumber')}")
                logger.info(f"  Check Number: {sample.get('checkNumber')}")
                logger.info(f"  Payment Date: {sample.get('paymentDate')}")
                logger.info(f"  Amount: {sample.get('amount')}")
            return 0
        
        # Update payments with progress bar
        with click.progressbar(
            payments,
            label="Updating payments",
            length=total,
            show_pos=True,
        ) as bar:
            for payment in bar:
                customer_number = None
                check_number = None
                try:
                    customer_number = payment.get("customerNumber")
                    check_number = payment.get("checkNumber")
                    
                    if not customer_number or not check_number:
                        logger.warning("Payment missing customerNumber or checkNumber, skipping")
                        self.stats["payments_failed"] += 1
                        continue
                    
                    # Prepare update data (only date field)
                    # Note: API expects lowercase field names
                    update_data = {
                        "paymentdate": payment.get("paymentDate"),
                    }
                    
                    # Update via API
                    self.client.update_payment(customer_number, check_number, update_data)
                    self.stats["payments_updated"] += 1
                    
                except ClassicModelsAPIError as e:
                    logger.error(f"Failed to update payment {customer_number or 'unknown'}/{check_number or 'unknown'}: {e}")
                    self.stats["payments_failed"] += 1
                except Exception as e:
                    logger.error(f"Unexpected error updating payment {customer_number or 'unknown'}/{check_number or 'unknown'}: {e}")
                    self.stats["payments_failed"] += 1
        
        return self.stats["payments_updated"]
    
    def run(self, dry_run: bool = False, orders_only: bool = False, payments_only: bool = False) -> Dict[str, int]:
        """Run the complete update process.
        
        Args:
            dry_run: If True, only show what would be updated without making changes
            orders_only: If True, only update orders
            payments_only: If True, only update payments
        
        Returns:
            Dictionary with update statistics
        """
        logger.info("=" * 60)
        logger.info("Classic Models API Timestamp Updater")
        logger.info("=" * 60)
        
        if dry_run:
            logger.info("Running in DRY RUN mode - no changes will be made")
        
        # Verify connection
        logger.info("Verifying API connection...")
        try:
            self.client.verify_connection()
        except Exception as e:
            logger.error(f"Failed to connect to API: {e}")
            raise
        
        # Update orders
        if not payments_only:
            try:
                self.update_orders(dry_run=dry_run)
            except FileNotFoundError as e:
                logger.error(str(e))
                raise
            except Exception as e:
                logger.error(f"Error updating orders: {e}")
        
        # Update payments
        if not orders_only:
            try:
                self.update_payments(dry_run=dry_run)
            except FileNotFoundError as e:
                logger.error(str(e))
                raise
            except Exception as e:
                logger.error(f"Error updating payments: {e}")
        
        # Logout
        self.client.logout()
        
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("Update Summary")
        logger.info("=" * 60)
        
        if not payments_only:
            logger.info(f"Orders updated: {self.stats['orders_updated']}")
            if self.stats['orders_failed'] > 0:
                logger.warning(f"Orders failed: {self.stats['orders_failed']}")
        
        if not orders_only:
            logger.info(f"Payments updated: {self.stats['payments_updated']}")
            if self.stats['payments_failed'] > 0:
                logger.warning(f"Payments failed: {self.stats['payments_failed']}")
        
        total_updated = self.stats['orders_updated'] + self.stats['payments_updated']
        total_failed = self.stats['orders_failed'] + self.stats['payments_failed']
        
        logger.info(f"\nTotal updated: {total_updated}")
        if total_failed > 0:
            logger.warning(f"Total failed: {total_failed}")
        
        if not dry_run:
            logger.info("\n✓ Update completed successfully!")
        else:
            logger.info("\n✓ Dry run completed!")
        
        logger.info("=" * 60)
        
        return self.stats


# Made with Bob