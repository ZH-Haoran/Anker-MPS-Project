from util.header import *
import os
import pandas as pd


class DataReader:
    def __init__(self):
        self._excel_data_paths_dict = self._generate_excel_data_paths()
        self._data_dict = self._read_raw_data()
        self._init_clean()

    def get_excel_data_paths_dict(self):
        return self._excel_data_paths_dict
    
    def get_data_dict(self):
        return self._data_dict

    def _generate_excel_data_paths(self):
        base_dir = "/Users/anker/MPS_algo/data/raw"
        
        excel_data_paths_dict = {}
        def get_full_path(file_name):
            file_name = ''.join((file_name, '.xlsx'))
            return os.path.join(base_dir, file_name)
        
        excel_data_paths_dict[TableName.ANKER_WEEK] = get_full_path(TableName.ANKER_WEEK)
        excel_data_paths_dict[TableName.FACTORY_CAPACITY] = get_full_path(TableName.FACTORY_CAPACITY)
        excel_data_paths_dict[TableName.FACTORY_PRODUCTION_DAYS] = get_full_path(TableName.FACTORY_PRODUCTION_DAYS)
        excel_data_paths_dict[TableName.CURRENT_INVENTORY] = get_full_path(TableName.CURRENT_INVENTORY)
        excel_data_paths_dict[TableName.INTRANSIT_PO] = get_full_path(TableName.INTRANSIT_PO)
        excel_data_paths_dict[TableName.SKU_MAIN] = get_full_path(TableName.SKU_MAIN)
        excel_data_paths_dict[TableName.SOP_PREDICTION] = get_full_path(TableName.SOP_PREDICTION)

        return excel_data_paths_dict


    def _read_raw_data(self):
        _data_dict = {}
        for table_name, table_path in self._excel_data_paths_dict.items():
            _data_dict[table_name] = pd.read_excel(table_path)

        return _data_dict
    

    def _init_clean(self):
        self._init_clean_capacity()
        self._init_clean_schedule()
        self._init_clean_current_inventory()
        self._init_clean_intransit_PO()
        self._init_clean_sku_main()
        self._init_clean_SOP()


    def _init_clean_capacity(self):
        capacity_df = self._data_dict[TableName.FACTORY_CAPACITY]
        capacity_df = capacity_df.dropna(how='any')
        capacity_df = capacity_df.drop_duplicates(subset=[
            FactoryCapacity.PN, FactoryCapacity.SUPPLY_CENTER, FactoryCapacity.FACTORY, FactoryCapacity.PRODUCT_LINE
            ], keep='first')
        
        self._data_dict[TableName.FACTORY_CAPACITY] = capacity_df
    

    def _init_clean_schedule(self):
        schedule_df = self._data_dict[TableName.FACTORY_PRODUCTION_DAYS]
        schedule_df = schedule_df.dropna(subset=[FactoryProductionDays.FACTORY])
        week_cols = [col for col in schedule_df.columns if col.startswith('20')]
        for col in week_cols:
            schedule_df[col] = pd.to_numeric(schedule_df[col], errors='coerce')
        schedule_df = schedule_df.dropna(subset=week_cols)
        schedule_df = schedule_df.drop_duplicates(subset=[FactoryProductionDays.FACTORY], keep='first')

        self._data_dict[TableName.FACTORY_PRODUCTION_DAYS] = schedule_df


    def _init_clean_current_inventory(self):
        current_inventory_df = self._data_dict[TableName.CURRENT_INVENTORY]
        current_inventory_df = current_inventory_df.drop_duplicates(subset=[CurrentInventory.SKU, CurrentInventory.SUPPLY_CENTER], keep='first')

        self._data_dict[TableName.CURRENT_INVENTORY] = current_inventory_df
    

    def _init_clean_intransit_PO(self):
        PO_df = self._data_dict[TableName.INTRANSIT_PO]
        PO_df = PO_df.dropna(how='any')

        self._data_dict[TableName.INTRANSIT_PO] = PO_df


    def _init_clean_sku_main(self):
        sku_df = self._data_dict[TableName.SKU_MAIN]
    
        # Filter rows where SKU is not null
        sku_df = sku_df[sku_df[SKUMain.SKU].notna()]
        
        # Update the cleaned DataFrame in the data dictionary
        self._data_dict[TableName.SKU_MAIN] = sku_df


    def _init_clean_SOP(self):
        sop_df = self._data_dict[TableName.SOP_PREDICTION]
        sop_df = sop_df[sop_df[SOP_PREDICTION.SKU].notna()]

        rename_dict = {}
        for col in sop_df.columns:
            # 检查列名是否包含 "-"，因为我们要处理类似 "2024W50-12/08" 的格式
            if '-' in col:
                # 以 "-" 分割列名，取前半部分
                new_col = col.split('-')[0]
                rename_dict[col] = new_col
            else:
                # 如果没有 "-"，保持原样
                rename_dict[col] = col
        sop_df.rename(columns=rename_dict, inplace=True)

        date_columns = [col for col in sop_df.columns if col.startswith('20') and 'W' in col]
        sop_df['non_zero_count'] = (sop_df[date_columns] != 0).sum(axis=1)
        sop_df = sop_df.loc[sop_df.groupby([SOP_PREDICTION.SKU, SOP_PREDICTION.SUPPLY_CENTER])['non_zero_count'].idxmax()]
        sop_df = sop_df.drop(columns=['non_zero_count'])
        
        self._data_dict[TableName.SOP_PREDICTION] = sop_df

