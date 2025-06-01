"""
Data loading module for the DA model parameters.
"""

import os
import pandas as pd
from typing import Dict, Tuple
import logging

from config.settings import FILE_NAMES

logger = logging.getLogger(__name__)


class DataLoader:
    """Handles loading of Excel files for DA model."""

    def __init__(self, base_directory: str):
        """
        Initialize the DataLoader.

        Args:
            base_directory (str): Path to the directory containing the Excel files
        """
        self.base_directory = base_directory
        self._validate_directory()

    def _validate_directory(self) -> None:
        """Validate that the base directory exists and contains required files."""
        if not os.path.exists(self.base_directory):
            raise FileNotFoundError(f"Directory not found: {self.base_directory}")

        missing_files = []
        for file_type, filename in FILE_NAMES.items():
            file_path = os.path.join(self.base_directory, filename)
            if not os.path.exists(file_path):
                missing_files.append(filename)

        if missing_files:
            raise FileNotFoundError(f"Missing required files: {missing_files}")

    def load_inventory(self) -> pd.DataFrame:
        """
        Load inventory data from Excel file.

        Returns:
            pd.DataFrame: Raw inventory data
        """
        file_path = os.path.join(self.base_directory, FILE_NAMES['inventory'])
        logger.info(f"Loading inventory data from {file_path}")

        try:
            return pd.read_excel(file_path)
        except Exception as e:
            logger.error(f"Error loading inventory data: {e}")
            raise

    def load_orders(self) -> pd.DataFrame:
        """
        Load order data from Excel file.

        Returns:
            pd.DataFrame: Raw order data
        """
        file_path = os.path.join(self.base_directory, FILE_NAMES['order'])
        logger.info(f"Loading order data from {file_path}")

        try:
            return pd.read_excel(file_path, sheet_name='脱敏数据')
        except Exception as e:
            logger.error(f"Error loading order data: {e}")
            raise

    def load_purchase_orders(self) -> pd.DataFrame:
        """
        Load purchase order data from Excel file.

        Returns:
            pd.DataFrame: Raw purchase order data
        """
        file_path = os.path.join(self.base_directory, FILE_NAMES['po'])
        logger.info(f"Loading purchase order data from {file_path}")

        try:
            return pd.read_excel(file_path)
        except Exception as e:
            logger.error(f"Error loading purchase order data: {e}")
            raise

    def load_region_capacity(self) -> pd.DataFrame:
        """
        Load region capacity data from Excel file.

        Returns:
            pd.DataFrame: Raw region capacity data
        """
        file_path = os.path.join(self.base_directory, FILE_NAMES['region_capacity'])
        logger.info(f"Loading region capacity data from {file_path}")

        try:
            return pd.read_excel(file_path)
        except Exception as e:
            logger.error(f"Error loading region capacity data: {e}")
            raise

    def load_all(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Load all data files.

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
            (inventory, orders, purchase_orders, region_capacity)
        """
        logger.info("Loading all data files")

        inventory = self.load_inventory()
        orders = self.load_orders()
        purchase_orders = self.load_purchase_orders()
        region_capacity = self.load_region_capacity()

        logger.info("All data files loaded successfully")
        return inventory, orders, purchase_orders, region_capacity