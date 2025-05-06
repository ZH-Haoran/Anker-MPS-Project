import pandas as pd
import numpy as np
import os
from datetime import date



def clean_data(base_dir):
    """
    :parameter
     - base_dir (os.path)
         that contains the three main files:
            - 库存可用量快照.xlsx
            - 在途PO快照.xlsx
            - 履行订单快照.xlsx
            - 区域订单上限快照.xlsx
    :return:
        - cleaned_inventory: (dataframe)
                    (Columns: 'supply center', 'sku', 'inventory')
        - cleaned_po: (dataframe)
                    (Columns: 'fulfillment order code', 'order code', 'supply center',
                     'sku', 'quantity', 'EPD', 'RPD', 'region', 'unique code')
        - cleaned_order: (dataframe)
                    (Columns: 'po code', 'batch code', 'supply center', 'sku', 'quantity', 'arrival time')
        - cleaned_region_capacity: (dataframe)
                    (Columns:'sku','region', 'order limit')
    """



    # 库存可用量快照
    inventory_path = os.path.join(base_dir, '库存可用量快照导出.xlsx')
    inventory = pd.read_excel(inventory_path)
    inventory.rename(columns={'供应中心': 'supply center',
                              'SKU': 'sku',
                              '可用量': 'inventory'}, inplace=True)
    inventory.dropna(subset=['sku', 'supply center'], inplace=True)
    inventory.fillna(0, inplace=True)
    inventory.drop_duplicates(subset=['supply center', 'sku'], keep='first', inplace=True)




    # 履行订单快照
    order_path = os.path.join(base_dir, '履行订单快照导出 (5).xlsx')
    order = pd.read_excel(order_path, sheet_name='脱敏数据')
    order.rename(columns={'履行订单号': 'fulfillment order code',
                          '订单号': 'order code',
                          '供应中心': 'supply center',
                          'SKU': 'sku',
                          '数量': 'quantity',
                          '行EPD': 'EPD',
                          '区域': 'region'}, inplace=True)
    order = order[['fulfillment order code', 'order code', 'supply center', 'sku', 'quantity', 'EPD', 'RPD', 'region']]
    order.dropna(inplace=True)
    order['RPD'] = pd.to_datetime(order['RPD']).dt.date
    order['EPD'] = pd.to_datetime(order['EPD']).dt.date
    order = order[order['RPD'] <= order['EPD']]
    order = order[order['EPD'] <= date(2026, 1, 1)]
    order['fulfillment order code row'] = order.groupby('fulfillment order code').cumcount() + 1
    order['unique code'] = order.apply(lambda row: (row['fulfillment order code'], row['fulfillment order code row']),
                                       axis=1)




    # 在途PO工单快照
    po_path = os.path.join(base_dir, '在途PO工单快照导出 (1).xlsx')
    po = pd.read_excel(po_path)
    po = po[['PO/工单号', '批次号', '供应中心', 'SKU', '未入库数量', '要求到货时间']]
    po.rename(columns={'PO/工单号': 'po code',
                       '批次号': 'batch code',
                       '供应中心': 'supply center',
                       'SKU': 'sku',
                       '未入库数量': 'quantity',
                       '要求到货时间': 'arrival time'}, inplace=True)
    po.dropna(inplace=True)
    po['arrival time'] = pd.to_datetime(po['arrival time']).dt.date
    # po['unique code'] = po.apply(lambda row: (row['batch code']), axis=1)




    # 区域订单上限快照
    region_path = os.path.join(base_dir, '区域订单上限快照.xlsx')
    region_capacity = pd.read_excel(region_path)
    region_capacity.rename(columns={'SKU': 'sku',
                                    '区域': 'region',
                                    '数量': 'capacity'}, inplace=True)



    return inventory, order, po, region_capacity