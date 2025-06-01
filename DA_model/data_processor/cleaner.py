"""
Data cleaning module for the DA model parameters.
"""

import pandas as pd
import numpy as np
from datetime import date
from typing import Tuple
import logging

from config.settings import COLUMN_MAPPINGS, VALIDATION_CONFIG, OPTIMIZATION_CONFIG

logger = logging.getLogger(__name__)


class DataCleaner:
    """Handles data cleaning and preprocessing for DA model."""

    def __init__(self):
        """Initialize the DataCleaner."""
        self.column_mappings = COLUMN_MAPPINGS
        self.validation_config = VALIDATION_CONFIG
        self.max_date = OPTIMIZATION_CONFIG['max_date']

    def clean_inventory(self, inventory_df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean inventory data.

        Args:
            inventory_df (pd.DataFrame): Raw inventory data

        Returns:
            pd.DataFrame: Cleaned inventory data
        """
        logger.info("Cleaning inventory data")

        # Rename columns
        cleaned_df = inventory_df.rename(columns=self.column_mappings['inventory'])

        # Drop rows with missing critical values
        cleaned_df = cleaned_df.dropna(subset=['sku', 'supply_center'])

        # Fill missing inventory values with 0
        cleaned_df['inventory'] = cleaned_df['inventory'].fillna(0)

        # Remove duplicates, keeping first occurrence
        cleaned_df = cleaned_df.drop_duplicates(
            subset=['supply_center', 'sku'],
            keep='first'
        )

        logger.info(f"Inventory data cleaned: {len(cleaned_df)} records")
        return cleaned_df

    def clean_orders(self, orders_df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean order data.

        Args:
            orders_df (pd.DataFrame): Raw order data

        Returns:
            pd.DataFrame: Cleaned order data
        """
        logger.info("Cleaning order data")

        # Rename columns
        cleaned_df = orders_df.rename(columns=self.column_mappings['order'])

        # Select required columns
        required_cols = [
            'fulfillment_order_code', 'order_code', 'supply_center',
            'sku', 'quantity', 'EPD', 'RPD', 'region'
        ]
        cleaned_df = cleaned_df[required_cols]

        # Drop rows with any missing values
        cleaned_df = cleaned_df.dropna()

        # Convert date columns
        cleaned_df['RPD'] = pd.to_datetime(cleaned_df['RPD']).dt.date
        cleaned_df['EPD'] = pd.to_datetime(cleaned_df['EPD']).dt.date

        # Filter based on date constraints
        cleaned_df = cleaned_df[cleaned_df['RPD'] <= cleaned_df['EPD']]
        cleaned_df = cleaned_df[cleaned_df['EPD'] <= self.max_date]

        # Create unique identifier for each order line
        cleaned_df['fulfillment_order_code_row'] = (
                cleaned_df.groupby('fulfillment_order_code').cumcount() + 1
        )
        cleaned_df['unique_code'] = list(zip(
            cleaned_df['fulfillment_order_code'],
            cleaned_df['fulfillment_order_code_row']
        ))

        logger.info(f"Order data cleaned: {len(cleaned_df)} records")
        return cleaned_df

    def clean_purchase_orders(self, po_df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean purchase order data.

        Args:
            po_df (pd.DataFrame): Raw purchase order data

        Returns:
            pd.DataFrame: Cleaned purchase order data
        """
        logger.info("Cleaning purchase order data")

        # Select and rename columns
        required_cols = ['PO/工单号', '批次号', '供应中心', 'SKU', '未入库数量', '要求到货时间']
        cleaned_df = po_df[required_cols].copy()
        cleaned_df = cleaned_df.rename(columns=self.column_mappings['po'])

        # Drop rows with missing values
        cleaned_df = cleaned_df.dropna()

        # Convert arrival time to date
        cleaned_df['arrival_time'] = pd.to_datetime(cleaned_df['arrival_time']).dt.date

        logger.info(f"Purchase order data cleaned: {len(cleaned_df)} records")
        return cleaned_df

    def clean_region_capacity(self, region_df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean region capacity data.

        Args:
            region_df (pd.DataFrame): Raw region capacity data

        Returns:
            pd.DataFrame: Cleaned region capacity data
        """
        logger.info("Cleaning region capacity data")

        # Rename columns
        cleaned_df = region_df.rename(columns=self.column_mappings['region_capacity'])

        # Drop rows with missing values
        cleaned_df = cleaned_df.dropna()

        logger.info(f"Region capacity data cleaned: {len(cleaned_df)} records")
        return cleaned_df

    def clean_all(self, inventory_df: pd.DataFrame, orders_df: pd.DataFrame,
                  po_df: pd.DataFrame, region_df: pd.DataFrame) -> Tuple[
        pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Clean all data.

        Args:
            inventory_df (pd.DataFrame): Raw inventory data
            orders_df (pd.DataFrame): Raw order data
            po_df (pd.DataFrame): Raw purchase order data
            region_df (pd.DataFrame): Raw region capacity data

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
            Cleaned (inventory, orders, purchase_orders, region_capacity)
        """
        logger.info("Starting data cleaning process")

        cleaned_inventory = self.clean_inventory(inventory_df)
        cleaned_orders = self.clean_orders(orders_df)
        cleaned_po = self.clean_purchase_orders(po_df)
        cleaned_region = self.clean_region_capacity(region_df)

        logger.info("Data cleaning process completed")
        return cleaned_inventory, cleaned_orders, cleaned_po, cleaned_region

    def validate_data(self, df: pd.DataFrame, data_type: str) -> bool:
        """
        Validate that a DataFrame has the required columns.

        Args:
            df (pd.DataFrame): DataFrame to validate
            data_type (str): Type of data ('inventory', 'order', 'po', 'region_capacity')

        Returns:
            bool: True if valid, False otherwise
        """
        required_columns = self.validation_config['required_columns'].get(data_type, [])
        missing_columns = set(required_columns) - set(df.columns)

        if missing_columns:
            logger.error(f"Missing columns in {data_type} data: {missing_columns}")
            return False

        logger.info(f"{data_type} data validation passed")
        return True