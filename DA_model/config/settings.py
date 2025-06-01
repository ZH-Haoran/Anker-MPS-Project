"""
Configuration settings for the DA model.
"""

from datetime import date
from typing import Dict, Any

# File names and paths
FILE_NAMES = {
    'inventory': '库存可用量快照导出.xlsx',
    'order': '履行订单快照导出.xlsx',
    'po': '在途PO工单快照导出.xlsx',
    'region_capacity': '区域订单上限快照.xlsx'
}

# Column mappings for data cleaning
COLUMN_MAPPINGS = {
    'inventory': {
        '供应中心': 'supply_center',
        'SKU': 'sku',
        '可用量': 'inventory'
    },
    'order': {
        '履行订单号': 'fulfillment_order_code',
        '订单号': 'order_code',
        '供应中心': 'supply_center',
        'SKU': 'sku',
        '数量': 'quantity',
        '行EPD': 'EPD',
        '区域': 'region'
    },
    'po': {
        'PO/工单号': 'po_code',
        '批次号': 'batch_code',
        '供应中心': 'supply_center',
        'SKU': 'sku',
        '未入库数量': 'quantity',
        '要求到货时间': 'arrival_time'
    },
    'region_capacity': {
        'SKU': 'sku',
        '区域': 'region',
        '数量': 'capacity'
    }
}

# Optimization parameters
OPTIMIZATION_CONFIG = {
    'rpd_penalty': 1,
    'epd_penalty': 10,
    'max_date': date(2026, 1, 1),
    'solver_timeout': 500  # seconds
}

# Data validation settings
VALIDATION_CONFIG = {
    'required_columns': {
        'inventory': ['supply_center', 'sku', 'inventory'],
        'order': ['fulfillment_order_code', 'order_code', 'supply_center', 'sku', 'quantity', 'EPD', 'RPD', 'region'],
        'po': ['po_code', 'batch_code', 'supply_center', 'sku', 'quantity', 'arrival_time'],
        'region_capacity': ['sku', 'region', 'capacity']
    }
}

# Logging configuration
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': 'delivery_optimization.log'
}