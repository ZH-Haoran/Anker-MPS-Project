"""
Data processing module for splitting data by SKU and preparing optimization parameters.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
import logging

from config.settings import OPTIMIZATION_CONFIG

logger = logging.getLogger(__name__)


class DataProcessor:
    """Processes cleaned data and prepares it for optimization by SKU."""

    def __init__(self):
        """Initialize the DataProcessor."""
        self.rpd_penalty = OPTIMIZATION_CONFIG['rpd_penalty']
        self.epd_penalty = OPTIMIZATION_CONFIG['epd_penalty']

    def get_unique_skus(self, orders_df: pd.DataFrame) -> List[str]:
        """
        Get unique SKUs from order data.

        Args:
            orders_df (pd.DataFrame): Cleaned order data

        Returns:
            List[str]: List of unique SKUs
        """
        return list(orders_df['sku'].unique())

    def filter_data_by_sku(self, inventory_df: pd.DataFrame, orders_df: pd.DataFrame,
                           po_df: pd.DataFrame, region_capacity_df: pd.DataFrame,
                           sku: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Filter all data for a specific SKU.

        Args:
            inventory_df (pd.DataFrame): Cleaned inventory data
            orders_df (pd.DataFrame): Cleaned order data
            po_df (pd.DataFrame): Cleaned purchase order data
            region_capacity_df (pd.DataFrame): Cleaned region capacity data
            sku (str): SKU to filter by

        Returns:
            Tuple of filtered DataFrames for the specific SKU
        """
        inventory_sku = inventory_df[inventory_df['sku'] == sku]
        orders_sku = orders_df[orders_df['sku'] == sku]
        po_sku = po_df[po_df['sku'] == sku]
        region_capacity_sku = region_capacity_df[region_capacity_df['sku'] == sku]

        return inventory_sku, orders_sku, po_sku, region_capacity_sku

    def create_time_set(self, orders_df: pd.DataFrame, po_df: pd.DataFrame) -> List:
        """
        Create a sorted list of unique time periods from order and PO data.

        Args:
            orders_df (pd.DataFrame): Order data for specific SKU
            po_df (pd.DataFrame): Purchase order data for specific SKU

        Returns:
            List: Sorted list of unique dates
        """
        times = pd.concat([
            po_df['arrival_time'],
            orders_df['RPD'],
            orders_df['EPD']
        ])
        unique_times = np.sort(times.unique())
        return list(unique_times)

    def create_region_set(self, orders_df: pd.DataFrame) -> List[str]:
        """
        Create list of unique regions.

        Args:
            orders_df (pd.DataFrame): Order data

        Returns:
            List[str]: List of unique regions
        """
        return list(orders_df['region'].unique())

    def create_optimization_parameters(self, inventory_df: pd.DataFrame, orders_df: pd.DataFrame,
                                       po_df: pd.DataFrame, region_capacity_df: pd.DataFrame,
                                       sku: str) -> Dict[str, Any]:
        """
        Create all parameters needed for optimization model.

        Args:
            inventory_df (pd.DataFrame): Inventory data for specific SKU
            orders_df (pd.DataFrame): Order data for specific SKU
            po_df (pd.DataFrame): Purchase order data for specific SKU
            region_capacity_df (pd.DataFrame): Region capacity data for specific SKU
            sku (str): SKU being processed

        Returns:
            Dict[str, Any]: Dictionary containing all optimization parameters
        """
        logger.info(f"Creating optimization parameters for SKU: {sku}")

        # Create time and region sets
        time_set = self.create_time_set(orders_df, po_df)
        region_set = self.create_region_set(orders_df)

        # Region capacity dictionary
        C_r = {}
        for region in region_set:
            capacity_data = region_capacity_df[region_capacity_df['region'] == region]
            if not capacity_data.empty:
                C_r[region] = capacity_data['capacity'].iloc[0]
            else:
                logger.warning(f"No capacity data found for region {region}, setting to 0")
                C_r[region] = 0

        # Inventory quantity
        I_p = {}
        if inventory_df.empty:
            I_p[sku] = 0
            logger.warning(f"No inventory data found for SKU {sku}, setting to 0")
        else:
            I_p[sku] = inventory_df['inventory'].iloc[0]

        # Purchase order data
        J = list(po_df['batch_code'].unique())

        Q_j = {}  # PO quantities
        t_j = {}  # PO arrival times
        for batch_code in J:
            po_data = po_df[po_df['batch_code'] == batch_code]
            Q_j[batch_code] = po_data['quantity'].iloc[0]
            t_j[batch_code] = po_data['arrival_time'].iloc[0]

        # Order data by region
        O_r = {}  # Orders by region
        for region in region_set:
            region_orders = orders_df[orders_df['region'] == region]
            O_r[region] = region_orders['unique_code'].tolist()

        # Order-specific data
        d_o = {}  # Order demands
        RPD_o = {}  # Order RPDs
        EPD_o = {}  # Order EPDs
        u_o = {}  # RPD penalties
        v_o = {}  # EPD penalties

        for region in region_set:
            for order_code in O_r[region]:
                order_data = orders_df[orders_df['unique_code'] == order_code]
                if not order_data.empty:
                    d_o[order_code] = order_data['quantity'].iloc[0]
                    RPD_o[order_code] = order_data['RPD'].iloc[0]
                    EPD_o[order_code] = order_data['EPD'].iloc[0]
                    u_o[order_code] = self.rpd_penalty
                    v_o[order_code] = self.epd_penalty

        parameters = {
            'T': time_set,
            'R': region_set,
            'C_r': C_r,
            'J': J,
            'I_p': I_p,
            'Q_j': Q_j,
            't_j': t_j,
            'O_r': O_r,
            'd_o': d_o,
            'RPD_o': RPD_o,
            'EPD_o': EPD_o,
            'u_o': u_o,
            'v_o': v_o,
            'sku': sku
        }

        logger.info(f"Optimization parameters created for SKU {sku}: "
                    f"{len(time_set)} time periods, {len(region_set)} regions, "
                    f"{len(J)} POs, {sum(len(orders) for orders in O_r.values())} orders")

        return parameters

    def process_sku(self, inventory_df: pd.DataFrame, orders_df: pd.DataFrame,
                    po_df: pd.DataFrame, region_capacity_df: pd.DataFrame,
                    sku: str) -> Optional[Dict[str, Any]]:
        """
        Process data for a single SKU and return optimization parameters.

        Args:
            inventory_df (pd.DataFrame): Cleaned inventory data
            orders_df (pd.DataFrame): Cleaned order data
            po_df (pd.DataFrame): Cleaned purchase order data
            region_capacity_df (pd.DataFrame): Cleaned region capacity data
            sku (str): SKU to process

        Returns:
            Optional[Dict[str, Any]]: Optimization parameters or None if no data
        """
        # Filter data for this SKU
        inventory_sku, orders_sku, po_sku, region_capacity_sku = self.filter_data_by_sku(
            inventory_df, orders_df, po_df, region_capacity_df, sku
        )

        # Check if we have any orders for this SKU
        if orders_sku.empty:
            logger.warning(f"No orders found for SKU {sku}, skipping")
            return None

        # Create optimization parameters
        return self.create_optimization_parameters(
            inventory_sku, orders_sku, po_sku, region_capacity_sku, sku
        )