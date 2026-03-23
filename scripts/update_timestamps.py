#!/usr/bin/env python3
"""
Classic Models Dataset Timestamp Updater

This script:
1. Parses the SQL file (with original 2003-2005 dates)
2. Transforms timestamps to current dates
3. Generates JSON files with updated data as a local cache

Strategy:
- Historical orders (Shipped/Resolved/Disputed/Cancelled): Map to last 18 months
- Future orders (In Process/On Hold): Map to next 3 months
- Preserve all date intervals and business logic
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


class TimestampUpdater:
    """Handles SQL parsing, timestamp transformation, and JSON generation."""
    
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
        self.json_dir = base_path / 'data' / 'json'
        
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
    
    def parse_sql_inserts(self, sql_content: str) -> Dict[str, List[Dict]]:
        """Parse SQL INSERT statements and extract data.
        
        Args:
            sql_content: String containing SQL statements
            
        Returns:
            Dictionary mapping table names to lists of records
        """
        tables_data = {}
        
        # Pattern to match INSERT statements
        insert_pattern = re.compile(
            r"insert\s+into\s+(\w+)\s*\(([^)]+)\)\s+values\s+(.*?);(?:\s*$|\s*\n)",
            re.IGNORECASE | re.MULTILINE
        )
        
        for match in insert_pattern.finditer(sql_content):
            table_name = match.group(1)
            columns_str = match.group(2)
            values_str = match.group(3)
            
            # Parse column names
            columns = [col.strip() for col in columns_str.split(',')]
            
            # Parse values
            records = self._parse_values(values_str, columns)
            
            if table_name in tables_data:
                tables_data[table_name].extend(records)
            else:
                tables_data[table_name] = records
        
        return tables_data
    
    def _parse_values(self, values_str: str, columns: List[str]) -> List[Dict]:
        """Parse VALUES clause into list of record dictionaries."""
        records = []
        i = 0
        
        while i < len(values_str):
            # Skip whitespace and commas
            while i < len(values_str) and values_str[i] in ' \t\n\r,':
                i += 1
            
            if i >= len(values_str):
                break
            
            # Look for opening parenthesis
            if values_str[i] == '(':
                paren_count = 1
                start = i + 1
                i += 1
                in_string = False
                string_char = None
                
                while i < len(values_str) and paren_count > 0:
                    char = values_str[i]
                    
                    if not in_string:
                        if char in ("'", '"'):
                            in_string = True
                            string_char = char
                        elif char == '(':
                            paren_count += 1
                        elif char == ')':
                            paren_count -= 1
                            if paren_count == 0:
                                break
                    else:
                        if char == '\\' and i + 1 < len(values_str):
                            next_char = values_str[i + 1]
                            if next_char in ("'", '"', '\\', 'n', 'r', 't', '0'):
                                i += 1
                        elif char == string_char:
                            if i + 1 < len(values_str) and values_str[i + 1] == string_char:
                                i += 1
                            else:
                                in_string = False
                                string_char = None
                    
                    i += 1
                
                row_str = values_str[start:i]
                values = self._parse_row_values(row_str)
                
                if len(values) == len(columns):
                    record = dict(zip(columns, values))
                    records.append(record)
                
                i += 1
            else:
                i += 1
        
        return records
    
    def _parse_row_values(self, row_str: str) -> List:
        """Parse a single row of values from SQL INSERT."""
        values = []
        current_value = []
        in_string = False
        was_quoted = False
        string_char = None
        i = 0
        
        while i < len(row_str):
            char = row_str[i]
            
            if not in_string:
                if char in ("'", '"'):
                    in_string = True
                    was_quoted = True
                    string_char = char
                    i += 1
                    continue
                elif char == ',':
                    value_str = ''.join(current_value).strip()
                    values.append(self._parse_value(value_str, was_quoted))
                    current_value = []
                    was_quoted = False
                    i += 1
                    continue
                else:
                    current_value.append(char)
                    i += 1
            else:
                if char == '\\' and i + 1 < len(row_str):
                    next_char = row_str[i + 1]
                    if next_char == "'":
                        current_value.append("'")
                        i += 2
                    elif next_char == '"':
                        current_value.append('"')
                        i += 2
                    elif next_char == '\\':
                        current_value.append('\\')
                        i += 2
                    elif next_char == 'n':
                        current_value.append('\n')
                        i += 2
                    elif next_char == 'r':
                        current_value.append('\r')
                        i += 2
                    elif next_char == 't':
                        current_value.append('\t')
                        i += 2
                    elif next_char == '0':
                        current_value.append('\0')
                        i += 2
                    else:
                        current_value.append(char)
                        i += 1
                elif char == string_char:
                    if i + 1 < len(row_str) and row_str[i + 1] == string_char:
                        current_value.append(char)
                        i += 2
                        continue
                    else:
                        in_string = False
                        string_char = None
                        i += 1
                else:
                    current_value.append(char)
                    i += 1
        
        if current_value:
            value_str = ''.join(current_value).strip()
            if value_str:
                values.append(self._parse_value(value_str, was_quoted))
        
        return values
    
    def _parse_value(self, value_str: str, is_quoted: bool):
        """Convert SQL value string to appropriate Python type."""
        if value_str.upper() == 'NULL':
            return None
        
        if is_quoted:
            return value_str
        
        try:
            if '.' in value_str:
                return float(value_str)
            else:
                return int(value_str)
        except ValueError:
            return value_str
    
    def transform_date(self, date_str: str, status: str) -> Optional[str]:
        """Transform a date based on order status.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            status: Order status
            
        Returns:
            Transformed date string in YYYY-MM-DD format, or None
        """
        if not date_str:
            return None
        
        original_date = datetime.strptime(date_str, '%Y-%m-%d')
        
        if status in self.HISTORICAL_STATUSES:
            # Map to historical range
            days_from_start = (original_date - self.ORIGINAL_START).days
            proportion = days_from_start / self.ORIGINAL_SPAN_DAYS
            new_days = int(proportion * self.HISTORICAL_SPAN_DAYS)
            new_date = self.HISTORICAL_START + timedelta(days=new_days)
        else:
            # Map to future range
            days_from_start = (original_date - self.ORIGINAL_START).days
            proportion = days_from_start / self.ORIGINAL_SPAN_DAYS
            new_days = int(proportion * self.FUTURE_SPAN_DAYS)
            new_date = self.FUTURE_START + timedelta(days=new_days)
        
        return new_date.strftime('%Y-%m-%d')
    
    def transform_orders(self, orders: List[Dict]) -> List[Dict]:
        """Transform order dates while preserving intervals."""
        transformed = []
        
        for order in orders:
            status = order['status']
            
            # Parse dates
            order_date = datetime.strptime(order['orderDate'], '%Y-%m-%d')
            required_date = datetime.strptime(order['requiredDate'], '%Y-%m-%d')
            shipped_date = datetime.strptime(order['shippedDate'], '%Y-%m-%d') if order.get('shippedDate') else None
            
            # Calculate intervals
            required_interval = (required_date - order_date).days
            shipped_interval = (shipped_date - order_date).days if shipped_date else None
            
            # Transform order date
            new_order_date_str = self.transform_date(order['orderDate'], status)
            if not new_order_date_str:
                continue
            new_order_date = datetime.strptime(new_order_date_str, '%Y-%m-%d')
            
            # Preserve intervals
            new_required_date = new_order_date + timedelta(days=required_interval)
            new_shipped_date = new_order_date + timedelta(days=shipped_interval) if shipped_interval is not None else None
            
            transformed_order = order.copy()
            transformed_order['orderDate'] = new_order_date.strftime('%Y-%m-%d')
            transformed_order['requiredDate'] = new_required_date.strftime('%Y-%m-%d')
            transformed_order['shippedDate'] = new_shipped_date.strftime('%Y-%m-%d') if new_shipped_date else None
            
            transformed.append(transformed_order)
        
        return transformed
    
    def transform_payments(self, payments: List[Dict]) -> List[Dict]:
        """Transform payment dates to align with historical timeline."""
        transformed = []
        
        for payment in payments:
            payment_date = datetime.strptime(payment['paymentDate'], '%Y-%m-%d')
            
            # Payments are always historical
            days_from_start = (payment_date - self.ORIGINAL_START).days
            proportion = days_from_start / self.ORIGINAL_SPAN_DAYS
            new_days = int(proportion * self.HISTORICAL_SPAN_DAYS)
            new_payment_date = self.HISTORICAL_START + timedelta(days=new_days)
            
            transformed_payment = payment.copy()
            transformed_payment['paymentDate'] = new_payment_date.strftime('%Y-%m-%d')
            
            transformed.append(transformed_payment)
        
        return transformed
    
    def run(self):
        """Execute the complete update process."""
        print("=" * 60)
        print("Classic Models Dataset Timestamp Updater")
        print("=" * 60)
        
        # Read SQL file
        print(f"\nReading SQL file: {self.sql_path}")
        with open(self.sql_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Parse all tables
        print("Parsing SQL file...")
        tables_data = self.parse_sql_inserts(sql_content)
        print(f"Found {len(tables_data)} tables")
        
        # Transform orders and payments
        if 'orders' in tables_data:
            print(f"\nTransforming {len(tables_data['orders'])} orders...")
            tables_data['orders'] = self.transform_orders(tables_data['orders'])
            print("✓ Orders transformed")
        
        if 'payments' in tables_data:
            print(f"Transforming {len(tables_data['payments'])} payments...")
            tables_data['payments'] = self.transform_payments(tables_data['payments'])
            print("✓ Payments transformed")
        
        # Ensure output directory exists
        self.json_dir.mkdir(parents=True, exist_ok=True)
        
        # Write JSON files
        print("\n" + "=" * 60)
        print("Writing JSON Files")
        print("=" * 60)
        
        for table_name, records in tables_data.items():
            output_file = self.json_dir / f"{table_name}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(records, f, indent=2, ensure_ascii=False)
            print(f"✓ Created {output_file} with {len(records)} records")
        
        # Show date range summary
        if 'orders' in tables_data:
            order_dates = [datetime.strptime(o['orderDate'], '%Y-%m-%d') for o in tables_data['orders']]
            min_date = min(order_dates)
            max_date = max(order_dates)
            
            historical_count = sum(1 for o in tables_data['orders'] if o['status'] in self.HISTORICAL_STATUSES)
            future_count = sum(1 for o in tables_data['orders'] if o['status'] in self.FUTURE_STATUSES)
            
            print(f"\nDate range: {min_date.date()} to {max_date.date()}")
            print(f"Historical orders: {historical_count}")
            print(f"Future orders: {future_count}")
        
        print("\n" + "=" * 60)
        print("✓ Update completed successfully!")
        print("=" * 60)


def main():
    """Main entry point."""
    script_dir = Path(__file__).parent
    base_path = script_dir.parent
    
    updater = TimestampUpdater(base_path)
    updater.run()


if __name__ == '__main__':
    main()

# Made with Bob
