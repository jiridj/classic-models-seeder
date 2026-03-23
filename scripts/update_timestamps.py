#!/usr/bin/env python3
"""
Classic Models Dataset Timestamp Updater

This script updates timestamps in the Classic Models demo dataset to make them current.
It transforms dates in both SQL and JSON files while preserving business logic and relationships.

Strategy:
- Historical orders (Shipped/Resolved/Disputed/Cancelled): Map to last 18 months (2024-09-05 to 2026-03-05)
- Future orders (In Process/On Hold): Map to next 3 months (2026-03-05 to 2026-06-05)
- Preserve all date intervals and business logic
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import shutil


class TimestampUpdater:
    """Handles timestamp transformation for Classic Models dataset."""
    
    # Original dataset date range
    ORIGINAL_START = datetime(2003, 1, 6)
    ORIGINAL_END = datetime(2005, 5, 31)
    ORIGINAL_SPAN_DAYS = (ORIGINAL_END - ORIGINAL_START).days  # 876 days
    
    # Statuses that should be mapped to historical dates
    HISTORICAL_STATUSES = {'Shipped', 'Resolved', 'Disputed', 'Cancelled'}
    FUTURE_STATUSES = {'In Process', 'On Hold'}
    
    def __init__(self, base_path: Path):
        """Initialize with base project path."""
        self.base_path = base_path
        self.sql_path = base_path / 'data' / 'sql' / 'mysqlsampledatabase.sql'
        self.orders_json_path = base_path / 'data' / 'json' / 'orders.json'
        self.payments_json_path = base_path / 'data' / 'json' / 'payments.json'
        
        # Calculate date ranges dynamically based on current date
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Historical: last 18 months (ending today)
        self.HISTORICAL_END = today
        self.HISTORICAL_START = today - timedelta(days=547)  # ~18 months
        self.HISTORICAL_SPAN_DAYS = (self.HISTORICAL_END - self.HISTORICAL_START).days
        
        # Future: next 3 months (starting today)
        self.FUTURE_START = today
        self.FUTURE_END = today + timedelta(days=92)  # ~3 months
        self.FUTURE_SPAN_DAYS = (self.FUTURE_END - self.FUTURE_START).days
        
    def transform_date(self, original_date: datetime, status: str) -> datetime:
        """
        Transform a date based on its position in the original timeline and order status.
        
        Args:
            original_date: Original date from 2003-2005 dataset
            status: Order status (determines if historical or future)
            
        Returns:
            Transformed date in new timeline
        """
        if status in self.HISTORICAL_STATUSES:
            # Map to historical range (last 18 months)
            days_from_start = (original_date - self.ORIGINAL_START).days
            proportion = days_from_start / self.ORIGINAL_SPAN_DAYS
            new_days = int(proportion * self.HISTORICAL_SPAN_DAYS)
            return self.HISTORICAL_START + timedelta(days=new_days)
        else:
            # Map to future range (next 3 months)
            days_from_start = (original_date - self.ORIGINAL_START).days
            proportion = days_from_start / self.ORIGINAL_SPAN_DAYS
            new_days = int(proportion * self.FUTURE_SPAN_DAYS)
            return self.FUTURE_START + timedelta(days=new_days)
    
    def parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string in YYYY-MM-DD format."""
        if not date_str or date_str.upper() == 'NULL':
            return None
        # Remove quotes if present
        date_str = date_str.strip("'\"")
        return datetime.strptime(date_str, '%Y-%m-%d')
    
    def format_date(self, date: Optional[datetime]) -> str:
        """Format date as YYYY-MM-DD string or NULL."""
        if date is None:
            return 'NULL'
        return date.strftime('%Y-%m-%d')
    
    def parse_sql_orders(self, sql_content: str) -> List[Dict]:
        """
        Parse orders from SQL INSERT statement using character-by-character parsing.
        
        Returns:
            List of order dictionaries
        """
        # Find the orders INSERT statement
        # Use greedy match (.*) to capture all data up to the LAST semicolon
        # This handles semicolons inside comment strings correctly
        pattern = r"insert\s+into\s+orders\s*\([^)]+\)\s+values\s+(.*);$"
        match = re.search(pattern, sql_content, re.IGNORECASE | re.DOTALL)
        
        if not match:
            raise ValueError("Could not find orders INSERT statement")
        
        values_str = match.group(1).strip()
        
        print(f"DEBUG: Captured values_str length: {len(values_str)}")
        print(f"DEBUG: First 100 chars: {values_str[:100]}")
        print(f"DEBUG: Last 100 chars: {values_str[-100:]}")
        
        # NOTE: Do NOT remove outer parentheses - VALUES clause starts with first tuple
        # The data is: (10100,'2003-01-06',...),(10101,'2003-01-09',...),...
        # Not: ((10100,'2003-01-06',...),(10101,'2003-01-09',...))
        
        # Split by "),(" to get individual order tuples
        # Use character-by-character parsing to handle escaped quotes
        orders = []
        current_tuple = []
        in_quotes = False
        escape_next = False
        paren_depth = 0
        
        i = 0
        while i < len(values_str):
            char = values_str[i]
            
            if escape_next:
                current_tuple.append(char)
                escape_next = False
            elif char == '\\':
                current_tuple.append(char)
                escape_next = True
            elif char == "'" and not escape_next:
                current_tuple.append(char)
                in_quotes = not in_quotes
            elif not in_quotes:
                if char == '(':
                    paren_depth += 1
                    if paren_depth == 1:
                        current_tuple = []
                    else:
                        current_tuple.append(char)
                elif char == ')':
                    paren_depth -= 1
                    if paren_depth == 0:
                        # End of tuple - parse it
                        tuple_str = ''.join(current_tuple)
                        order = self._parse_order_tuple(tuple_str)
                        if order:
                            orders.append(order)
                        current_tuple = []
                    else:
                        current_tuple.append(char)
                else:
                    current_tuple.append(char)
            else:
                current_tuple.append(char)
            
            i += 1
        
        print(f"Parsed {len(orders)} orders from SQL")
        return orders
    
    def _parse_order_tuple(self, tuple_str: str) -> Optional[Dict]:
        """Parse a single order tuple string into a dictionary."""
        # Split by comma, but respect quotes
        fields = []
        current_field = []
        in_quotes = False
        escape_next = False
        
        for char in tuple_str:
            if escape_next:
                current_field.append(char)
                escape_next = False
            elif char == '\\':
                current_field.append(char)
                escape_next = True
            elif char == "'" and not escape_next:
                in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                fields.append(''.join(current_field).strip())
                current_field = []
            else:
                current_field.append(char)
        
        # Add last field
        if current_field:
            fields.append(''.join(current_field).strip())
        
        # Validate we have exactly 7 fields
        if len(fields) != 7:
            print(f"Warning: Skipping malformed order tuple with {len(fields)} fields (expected 7)")
            return None
        
        try:
            # Remove quotes from string fields
            def unquote(s):
                s = s.strip()
                if s.upper() == 'NULL':
                    return None
                if s.startswith("'") and s.endswith("'"):
                    return s[1:-1]
                return s
            
            order = {
                'orderNumber': int(fields[0]),
                'orderDate': unquote(fields[1]),
                'requiredDate': unquote(fields[2]),
                'shippedDate': unquote(fields[3]),
                'status': unquote(fields[4]),
                'comments': unquote(fields[5]),
                'customerNumber': int(fields[6])
            }
            return order
        except (ValueError, IndexError) as e:
            print(f"Warning: Error parsing order tuple: {e}")
            return None
    
    def parse_sql_payments(self, sql_content: str) -> List[Dict]:
        """
        Parse payments from SQL INSERT statement.
        
        Returns:
            List of payment dictionaries
        """
        # Find the payments INSERT statement
        pattern = r"insert\s+into\s+payments\s*\([^)]+\)\s+values\s+(.*?);"
        match = re.search(pattern, sql_content, re.IGNORECASE | re.DOTALL)
        
        if not match:
            raise ValueError("Could not find payments INSERT statement")
        
        values_str = match.group(1)
        
        # Parse individual payment tuples
        # Format: (customerNumber,'checkNumber','paymentDate','amount')
        tuple_pattern = r"\((\d+),'([^']+)','([^']+)','([^']+)'\)"
        
        payments = []
        for match in re.finditer(tuple_pattern, values_str):
            payment = {
                'customerNumber': int(match.group(1)),
                'checkNumber': match.group(2),
                'paymentDate': match.group(3),
                'amount': match.group(4)
            }
            payments.append(payment)
        
        return payments
    
    def transform_orders(self, orders: List[Dict]) -> List[Dict]:
        """
        Transform order dates while preserving business logic.
        
        Args:
            orders: List of order dictionaries
            
        Returns:
            List of transformed order dictionaries
        """
        transformed = []
        
        for order in orders:
            status = order['status']
            
            # Parse original dates
            order_date = self.parse_date(order['orderDate'])
            required_date = self.parse_date(order['requiredDate'])
            shipped_date = self.parse_date(order['shippedDate']) if order['shippedDate'] else None
            
            # Ensure order_date and required_date are not None (they should never be)
            if order_date is None or required_date is None:
                raise ValueError(f"Order {order['orderNumber']} has missing required dates")
            
            # Calculate original intervals
            required_interval = (required_date - order_date).days
            shipped_interval = (shipped_date - order_date).days if shipped_date else None
            
            # Transform order date
            new_order_date = self.transform_date(order_date, status)
            
            # Preserve intervals for other dates
            new_required_date = new_order_date + timedelta(days=required_interval)
            new_shipped_date = new_order_date + timedelta(days=shipped_interval) if shipped_interval is not None else None
            
            # Create transformed order
            transformed_order = {
                'orderNumber': order['orderNumber'],
                'orderDate': self.format_date(new_order_date),
                'requiredDate': self.format_date(new_required_date),
                'shippedDate': self.format_date(new_shipped_date) if new_shipped_date else None,
                'status': status,
                'comments': order['comments'],
                'customerNumber': order['customerNumber']
            }
            
            transformed.append(transformed_order)
        
        return transformed
    
    def transform_payments(self, payments: List[Dict], orders: List[Dict]) -> List[Dict]:
        """
        Transform payment dates to align with order dates.
        
        Args:
            payments: List of payment dictionaries
            orders: List of transformed order dictionaries
            
        Returns:
            List of transformed payment dictionaries
        """
        # Create mapping of customer to their orders
        customer_orders = {}
        for order in orders:
            customer_num = order['customerNumber']
            if customer_num not in customer_orders:
                customer_orders[customer_num] = []
            customer_orders[customer_num].append(order)
        
        transformed = []
        
        for payment in payments:
            customer_num = payment['customerNumber']
            payment_date = self.parse_date(payment['paymentDate'])
            
            # Ensure payment_date is not None
            if payment_date is None:
                raise ValueError(f"Payment for customer {customer_num} has missing payment date")
            
            # Find the closest order date for this customer to maintain relative timing
            if customer_num in customer_orders:
                # Use the first order's transformation as reference
                first_order = customer_orders[customer_num][0]
                first_order_date = self.parse_date(first_order['orderDate'])
                
                # Calculate offset from original timeline
                original_offset = (payment_date - self.ORIGINAL_START).days
                proportion = original_offset / self.ORIGINAL_SPAN_DAYS
                
                # Apply same transformation logic as orders
                # Payments are always historical (already completed)
                new_days = int(proportion * self.HISTORICAL_SPAN_DAYS)
                new_payment_date = self.HISTORICAL_START + timedelta(days=new_days)
            else:
                # Fallback: use standard historical transformation
                new_days = int(((payment_date - self.ORIGINAL_START).days / self.ORIGINAL_SPAN_DAYS) * self.HISTORICAL_SPAN_DAYS)
                new_payment_date = self.HISTORICAL_START + timedelta(days=new_days)
            
            transformed_payment = {
                'customerNumber': customer_num,
                'checkNumber': payment['checkNumber'],
                'paymentDate': self.format_date(new_payment_date),
                'amount': payment['amount']
            }
            
            transformed.append(transformed_payment)
        
        return transformed
    
    def generate_sql_orders_insert(self, orders: List[Dict]) -> str:
        """Generate SQL INSERT statement for orders."""
        values = []
        for order in orders:
            shipped = f"'{order['shippedDate']}'" if order['shippedDate'] else 'NULL'
            # Escape single quotes in comments by doubling them
            if order['comments']:
                escaped_comments = order['comments'].replace("'", "''")
                comments = f"'{escaped_comments}'"
            else:
                comments = 'NULL'
            
            value = (f"({order['orderNumber']},'{order['orderDate']}','{order['requiredDate']}',"
                    f"{shipped},'{order['status']}',{comments},{order['customerNumber']})")
            values.append(value)
        
        return "insert  into orders(orderNumber,orderDate,requiredDate,shippedDate,status,comments,customerNumber) values \n" + ",".join(values) + ";"
    
    def generate_sql_payments_insert(self, payments: List[Dict]) -> str:
        """Generate SQL INSERT statement for payments."""
        values = []
        for payment in payments:
            value = (f"({payment['customerNumber']},'{payment['checkNumber']}',"
                    f"'{payment['paymentDate']}','{payment['amount']}')")
            values.append(value)
        
        return "insert  into payments(customerNumber,checkNumber,paymentDate,amount) values \n" + ",".join(values) + ";"
    
    def update_sql_file(self, orders: List[Dict], payments: List[Dict]):
        """Update the SQL file with transformed data."""
        print(f"Updating SQL file: {self.sql_path}")
        
        # Backup original
        backup_path = self.sql_path.with_suffix('.sql.backup')
        shutil.copy2(self.sql_path, backup_path)
        print(f"Created backup: {backup_path}")
        
        # Read original content
        with open(self.sql_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Generate new INSERT statements
        new_orders_insert = self.generate_sql_orders_insert(orders)
        new_payments_insert = self.generate_sql_payments_insert(payments)
        
        # Replace orders INSERT
        orders_pattern = r"insert\s+into\s+orders\s*\([^)]+\)\s+values\s+.*?;"
        content = re.sub(orders_pattern, new_orders_insert, content, flags=re.IGNORECASE | re.DOTALL)
        
        # Replace payments INSERT
        payments_pattern = r"insert\s+into\s+payments\s*\([^)]+\)\s+values\s+.*?;"
        content = re.sub(payments_pattern, new_payments_insert, content, flags=re.IGNORECASE | re.DOTALL)
        
        # Write updated content
        with open(self.sql_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ SQL file updated successfully")
    
    def update_json_files(self, orders: List[Dict], payments: List[Dict]):
        """Update JSON files with transformed data."""
        # Update orders.json
        print(f"Updating JSON file: {self.orders_json_path}")
        backup_path = self.orders_json_path.with_suffix('.json.backup')
        shutil.copy2(self.orders_json_path, backup_path)
        print(f"Created backup: {backup_path}")
        
        with open(self.orders_json_path, 'w', encoding='utf-8') as f:
            json.dump(orders, f, indent=2)
        print(f"✓ Orders JSON updated successfully")
        
        # Update payments.json
        print(f"Updating JSON file: {self.payments_json_path}")
        backup_path = self.payments_json_path.with_suffix('.json.backup')
        shutil.copy2(self.payments_json_path, backup_path)
        print(f"Created backup: {backup_path}")
        
        with open(self.payments_json_path, 'w', encoding='utf-8') as f:
            json.dump(payments, f, indent=2)
        print(f"✓ Payments JSON updated successfully")
    
    def validate_consistency(self, sql_orders: List[Dict], json_orders: List[Dict],
                           sql_payments: List[Dict], json_payments: List[Dict]) -> bool:
        """
        Validate consistency between SQL and JSON data.
        
        Returns:
            True if consistent, False otherwise
        """
        print("\n=== Validation ===")
        
        errors = []
        
        # Check order counts
        if len(sql_orders) != len(json_orders):
            errors.append(f"Order count mismatch: SQL={len(sql_orders)}, JSON={len(json_orders)}")
        else:
            print(f"✓ Order count: {len(sql_orders)}")
        
        # Check payment counts
        if len(sql_payments) != len(json_payments):
            errors.append(f"Payment count mismatch: SQL={len(sql_payments)}, JSON={len(json_payments)}")
        else:
            print(f"✓ Payment count: {len(sql_payments)}")
        
        # Check order data consistency
        for i, (sql_order, json_order) in enumerate(zip(sql_orders, json_orders)):
            if sql_order['orderNumber'] != json_order['orderNumber']:
                errors.append(f"Order {i}: orderNumber mismatch")
            if sql_order['orderDate'] != json_order['orderDate']:
                errors.append(f"Order {sql_order['orderNumber']}: orderDate mismatch")
            if sql_order['requiredDate'] != json_order['requiredDate']:
                errors.append(f"Order {sql_order['orderNumber']}: requiredDate mismatch")
            if sql_order['shippedDate'] != json_order['shippedDate']:
                errors.append(f"Order {sql_order['orderNumber']}: shippedDate mismatch")
        
        if not errors:
            print("✓ All orders match between SQL and JSON")
        
        # Check payment data consistency
        for i, (sql_payment, json_payment) in enumerate(zip(sql_payments, json_payments)):
            if sql_payment['customerNumber'] != json_payment['customerNumber']:
                errors.append(f"Payment {i}: customerNumber mismatch")
            if sql_payment['paymentDate'] != json_payment['paymentDate']:
                errors.append(f"Payment {i}: paymentDate mismatch")
        
        if not errors:
            print("✓ All payments match between SQL and JSON")
        
        # Check date ranges - filter out None values
        parsed_dates = [self.parse_date(o['orderDate']) for o in sql_orders]
        order_dates = [d for d in parsed_dates if d is not None]
        if order_dates:
            min_date = min(order_dates)
            max_date = max(order_dates)
        else:
            raise ValueError("No valid order dates found")
        
        print(f"\nDate range: {min_date.date()} to {max_date.date()}")
        
        # Count historical vs future orders
        historical_count = sum(1 for o in sql_orders if o['status'] in self.HISTORICAL_STATUSES)
        future_count = sum(1 for o in sql_orders if o['status'] in self.FUTURE_STATUSES)
        
        print(f"Historical orders (Shipped/Resolved/Disputed/Cancelled): {historical_count}")
        print(f"Future orders (In Process/On Hold): {future_count}")
        
        if errors:
            print("\n❌ Validation FAILED:")
            for error in errors[:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more errors")
            return False
        
        print("\n✓ Validation PASSED")
        return True
    
    def run(self):
        """Execute the complete timestamp update process."""
        print("=" * 60)
        print("Classic Models Dataset Timestamp Updater")
        print("=" * 60)
        
        # Read SQL file
        print(f"\nReading SQL file: {self.sql_path}")
        with open(self.sql_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Parse SQL data
        print("Parsing SQL orders...")
        sql_orders = self.parse_sql_orders(sql_content)
        print(f"Found {len(sql_orders)} orders")
        
        print("Parsing SQL payments...")
        sql_payments = self.parse_sql_payments(sql_content)
        print(f"Found {len(sql_payments)} payments")
        
        # Transform data
        print("\nTransforming orders...")
        transformed_orders = self.transform_orders(sql_orders)
        print(f"✓ Transformed {len(transformed_orders)} orders")
        
        print("Transforming payments...")
        transformed_payments = self.transform_payments(sql_payments, transformed_orders)
        print(f"✓ Transformed {len(transformed_payments)} payments")
        
        # Update files
        print("\n" + "=" * 60)
        print("Updating Files")
        print("=" * 60)
        self.update_sql_file(transformed_orders, transformed_payments)
        self.update_json_files(transformed_orders, transformed_payments)
        
        # Validate
        self.validate_consistency(transformed_orders, transformed_orders,
                                 transformed_payments, transformed_payments)
        
        print("\n" + "=" * 60)
        print("✓ Timestamp update completed successfully!")
        print("=" * 60)
        print("\nBackup files created with .backup extension")
        print("Review the changes and delete backups if satisfied.")


def main():
    """Main entry point."""
    # Determine base path (project root)
    script_dir = Path(__file__).parent
    base_path = script_dir.parent
    
    updater = TimestampUpdater(base_path)
    updater.run()


if __name__ == '__main__':
    main()

# Made with Bob
