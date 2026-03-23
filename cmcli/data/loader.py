"""Data loading utilities for Classic Models dataset."""

import json
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DataLoader:
    """Load Classic Models data from JSON files."""
    
    def __init__(self, data_dir: Path):
        """Initialize data loader.
        
        Args:
            data_dir: Path to data directory containing JSON files
        """
        self.data_dir = data_dir
        self.json_dir = data_dir / "json"
        
        if not self.json_dir.exists():
            raise FileNotFoundError(f"JSON data directory not found: {self.json_dir}")
    
    def load_json_file(self, filename: str) -> List[Dict[str, Any]]:
        """Load a JSON file.
        
        Args:
            filename: Name of JSON file (e.g., 'customers.json')
        
        Returns:
            List of records from JSON file
        
        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
        """
        filepath = self.json_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")
        
        logger.debug(f"Loading data from {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Loaded {len(data)} records from {filename}")
        return data
    
    def load_customers(self) -> List[Dict[str, Any]]:
        """Load customer data.
        
        Returns:
            List of customer records
        """
        return self.load_json_file("customers.json")
    
    def load_orders(self) -> List[Dict[str, Any]]:
        """Load order data.
        
        Returns:
            List of order records
        """
        return self.load_json_file("orders.json")
    
    def load_order_details(self) -> List[Dict[str, Any]]:
        """Load order details data.
        
        Returns:
            List of order detail records
        """
        return self.load_json_file("orderdetails.json")
    
    def load_payments(self) -> List[Dict[str, Any]]:
        """Load payment data.
        
        Returns:
            List of payment records
        """
        return self.load_json_file("payments.json")
    
    def load_employees(self) -> List[Dict[str, Any]]:
        """Load employee data.
        
        Returns:
            List of employee records
        """
        return self.load_json_file("employees.json")
    
    def load_offices(self) -> List[Dict[str, Any]]:
        """Load office data.
        
        Returns:
            List of office records
        """
        return self.load_json_file("offices.json")
    
    def load_products(self) -> List[Dict[str, Any]]:
        """Load product data.
        
        Returns:
            List of product records
        """
        return self.load_json_file("products.json")
    
    def load_product_lines(self) -> List[Dict[str, Any]]:
        """Load product line data.
        
        Returns:
            List of product line records
        """
        return self.load_json_file("productlines.json")

# Made with Bob
