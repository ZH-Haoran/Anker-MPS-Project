from util.header import *
import os
import pandas as pd


class DataReader:
    def __init__(self):
        """
        初始化DataReader对象, 生成原始数据路径字典, 读取原始数据, 并进行初步清洗。
        处理逻辑：
        1. 生成各表Excel路径;
        2. 读取所有原始数据表为DataFrame;
        3. 对各表进行初步清洗（去重、去空、格式处理等）。
        """
        self._excel_data_paths_dict = self._generate_excel_data_paths()
        self._data_dict = self._read_raw_data()
        self._init_clean()

    def get_excel_data_paths_dict(self):
        """
        获取原始Excel数据路径的字典。
        """
        return self._excel_data_paths_dict
    
    def get_data_dict(self):
        """
        获取清洗后的数据字典。
        """
        return self._data_dict

    def _generate_excel_data_paths(self):
        """
        生成原始数据各表的Excel文件路径字典。
        """
        base_dir = "./data/raw"
        
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
        """
        读取所有原始Excel数据表, 返回数据字典。
        """
        _data_dict = {}
        for table_name, table_path in self._excel_data_paths_dict.items():
            _data_dict[table_name] = pd.read_excel(table_path)

        return _data_dict
    

    def _init_clean(self):
        self._init_clean_capacity()  # 清洗工厂产能数据表
        self._init_clean_schedule()  # 清洗工厂生产日历数据表
        self._init_clean_current_inventory()  # 清洗当前库存数据表
        self._init_clean_intransit_PO()  # 清洗在途采购订单数据表
        self._init_clean_sku_main()  # 清洗SKU主数据表
        self._init_clean_SOP()  # 清洗SOP预测数据表


    def _init_clean_capacity(self):
        """
        清洗工厂产能表：去除空值和重复行。
        处理逻辑：先去除任何空值，再按PN、供应中心、工厂、产线去重。
        """
        capacity_df = self._data_dict[TableName.FACTORY_CAPACITY]
        capacity_df = capacity_df.dropna(how='any')
        capacity_df = capacity_df.drop_duplicates(subset=[
            FactoryCapacity.PN, FactoryCapacity.SUPPLY_CENTER, FactoryCapacity.FACTORY, FactoryCapacity.PRODUCT_LINE
            ], keep='first')
        
        self._data_dict[TableName.FACTORY_CAPACITY] = capacity_df
    

    def _init_clean_schedule(self):
        """
        清洗工厂生产日历表：去除工厂为空的行、周数据为空的行、重复工厂行，并将周数据转为数值型。
        处理逻辑：
        1. 去除工厂名为空的行；
        2. 将所有周列转为数值型，去除周数据为空的行；
        3. 按工厂去重，保留首行。
        """
        schedule_df = self._data_dict[TableName.FACTORY_PRODUCTION_DAYS]
        schedule_df = schedule_df.dropna(subset=[FactoryProductionDays.FACTORY])
        week_cols = [col for col in schedule_df.columns if col.startswith('20')]
        for col in week_cols:
            schedule_df[col] = pd.to_numeric(schedule_df[col], errors='coerce')
        schedule_df = schedule_df.dropna(subset=week_cols)
        schedule_df = schedule_df.drop_duplicates(subset=[FactoryProductionDays.FACTORY], keep='first')

        self._data_dict[TableName.FACTORY_PRODUCTION_DAYS] = schedule_df


    def _init_clean_current_inventory(self):
        """
        清洗现有库存表：按SKU和供应中心去重。
        处理逻辑：以SKU和供应中心为唯一键去重，保留首行。
        """
        current_inventory_df = self._data_dict[TableName.CURRENT_INVENTORY]
        current_inventory_df = current_inventory_df.drop_duplicates(subset=[CurrentInventory.SKU, CurrentInventory.SUPPLY_CENTER], keep='first')

        self._data_dict[TableName.CURRENT_INVENTORY] = current_inventory_df
    

    def _init_clean_intransit_PO(self):
        """
        清洗在途PO表：去除包含空值的行。
        处理逻辑：直接去除任何包含空值的行。
        """
        PO_df = self._data_dict[TableName.INTRANSIT_PO]
        PO_df = PO_df.dropna(how='any')

        self._data_dict[TableName.INTRANSIT_PO] = PO_df


    def _init_clean_sku_main(self):
        """
        清洗SKU主表：去除SKU为空的行。
        处理逻辑：只保留SKU非空的行。
        """
        sku_df = self._data_dict[TableName.SKU_MAIN]
    
        # Filter rows where SKU is not null
        sku_df = sku_df[sku_df[SKUMain.SKU].notna()]
        
        # Update the cleaned DataFrame in the data dictionary
        self._data_dict[TableName.SKU_MAIN] = sku_df


    def _init_clean_SOP(self):
        """
        清洗SOP预测表：
        1. 去除SKU为空的行；
        2. 处理带日期的列名（如"2024W50-12/08"只保留"2024W50"）；
        3. 对每组SKU+供应中心，保留非零周数最多的那一行（去重）。
        处理逻辑：
        - 先去除SKU为空的行；
        - 对所有列名，若包含"-"，只保留"-"前的部分；
        - 统计每行非零周数，分组后保留非零周数最多的那一行；
        - 去除辅助统计列。
        """
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

