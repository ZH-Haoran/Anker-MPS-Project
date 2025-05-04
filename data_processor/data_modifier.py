from util.header import *
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import re


class DataModifier:
    def __init__(self, data_dict, start_week: str, T: int):
        self._data_dict = data_dict
        self._start_week = start_week  # E.g.: "2025W1"
        self._time_span = T

        self._duration = self._generate_week_schedule()
        self._generate_real_date_to_anker_week_mapping()

        self._modify_data_dict()
        self._save_modified_data_dict()


    def get_modified_data_dict(self):
        return self._data_dict
    

    def get_plan_start_week(self):
        return self._start_week
    
    
    def get_plan_duration(self):
        return self._duration
    

    def _save_modified_data_dict(self):
        data_dict = self._data_dict
        base_dir = "/Users/anker/MPS_algo/data/modified"
        for supply_center, data in data_dict.items():
            supply_center_dir = os.path.join(base_dir, supply_center)
            if not os.path.exists(supply_center_dir):
                os.makedirs(supply_center_dir)

            for table_name, df in data.items():
                file_path = os.path.join(supply_center_dir, f"{table_name}.xlsx")
                df.to_excel(file_path, index=False)
        
        print(f"Modified data saved to {base_dir}.")


    def _modify_data_dict(self):
        # 由于 SKU 主数据表中没有 SLA_T 列，临时添加一列全 1 的数据作为运输 SLA
        self._add_SLA_T_to_sku_main_table()

        self._generate_week_capacity_within_duration()
        self._sum_capacities_of_each_factory()
        self._split_data_by_supply_center()
        self._filter_valid_skus()
        self._fill_MOQ_to_sku_main()
        self._merge_current_inventory_into_sku_main()
        self._remove_unmatched_skus_in_po_df()
        self._generate_arrival_week_quantity_to_PO_table()
        self._add_model_week_col_to_PO_table()
        self._add_capacity_occupied_week_to_PO_table()
        self._filter_demand_out_of_time_span()
        self._update_required_inventory_level_to_sop_prediction_table()


    # 由于 SKU 主数据表中没有 SLA_T 列，临时添加一列全 1 的数据作为运输 SLA
    def _add_SLA_T_to_sku_main_table(self):
        sku_df = self._data_dict[TableName.SKU_MAIN]
        sku_df[SKUMain.SLA_T] = np.ones(len(sku_df), dtype=int)
        self._data_dict[TableName.SKU_MAIN] = sku_df


    def _generate_week_capacity_within_duration(self):
        factory_capacity_df = self._data_dict[TableName.FACTORY_CAPACITY]
        factory_schedule_df = self._data_dict[TableName.FACTORY_PRODUCTION_DAYS]

        kept_cols = [col for col in factory_schedule_df.columns if (col.startswith('20') and col in self._duration) or not col.startswith('20')]
        factory_schedule_df = factory_schedule_df[kept_cols]

        assert FactoryCapacity.FACTORY == FactoryProductionDays.FACTORY
        capacity_schedule_merged_df = factory_capacity_df.merge(factory_schedule_df, on=FactoryCapacity.FACTORY, how='inner')

        week_capacity_df = capacity_schedule_merged_df[
            [FactoryCapacity.BG, FactoryCapacity.PDT, FactoryCapacity.PN, FactoryCapacity.SUPPLY_CENTER, FactoryCapacity.FACTORY, FactoryCapacity.PRODUCT_LINE]
            ].copy()

        weeks = [col for col in factory_schedule_df.columns if col.startswith('20')]
        for week in weeks:            
            week_capacity_df[week] = capacity_schedule_merged_df[FactoryCapacity.UPH] * \
                            capacity_schedule_merged_df[FactoryCapacity.HOURS_PER_SHIFT] * \
                            capacity_schedule_merged_df[FactoryCapacity.SHIFTS_PER_DAY_PER_LINE] * \
                            capacity_schedule_merged_df[FactoryCapacity.AVAILABLE_LINE_COUNT] * \
                            capacity_schedule_merged_df[week]

        # Check whether the week capacity is duplicated
        duplicate_rows = week_capacity_df.duplicated(subset=[
            WeekCapacity.PN, WeekCapacity.SUPPLY_CENTER, WeekCapacity.FACTORY, WeekCapacity.PRODUCT_LINE
            ], keep=False)
        assert len(duplicate_rows[duplicate_rows != False].index.tolist()) == 0

        # week_capacity_df[WeekCapacity.SP_PL_PAIR] = week_capacity_df[[WeekCapacity.FACTORY, WeekCapacity.PRODUCT_LINE]].apply(tuple, axis=1)

        self._data_dict[TableName.WEEK_CAPACITY] = week_capacity_df


    def _sum_capacities_of_each_factory(self):
        week_capacity_df = self._data_dict[TableName.WEEK_CAPACITY]

        factory_capacity_df = pd.DataFrame()
        grouped = week_capacity_df.groupby([WeekCapacity.PN, WeekCapacity.SUPPLY_CENTER, WeekCapacity.FACTORY])
        for _, group in grouped:
            group_copy = group.copy()
            week_cols = [col for col in group.columns if col.startswith('20')]
            for week in week_cols:
                group_copy[week] = group[week].sum()
            factory_capacity_df = pd.concat([factory_capacity_df, group_copy])

        factory_capacity_df = factory_capacity_df.drop_duplicates(subset=[WeekCapacity.PN, WeekCapacity.SUPPLY_CENTER, WeekCapacity.FACTORY])
        factory_capacity_df = factory_capacity_df.drop(columns=[WeekCapacity.PRODUCT_LINE])

        self._data_dict[TableName.WEEK_CAPACITY] = factory_capacity_df


    def _split_data_by_supply_center(self):
        splited_data_dict = {}

        # SKU主数据
        sku_main_df = self._data_dict[TableName.SKU_MAIN]
        supply_center_set = list(sku_main_df[SKUMain.SUPPLY_CENTER].unique())

        for supply_center in supply_center_set:
            sku_in_one_supply_center_df = sku_main_df[sku_main_df[SKUMain.SUPPLY_CENTER] == supply_center]
            splited_data_dict[supply_center] = {TableName.SKU_MAIN: sku_in_one_supply_center_df}
        
        # 工厂周产能数据
        week_capacity_df = self._data_dict[TableName.WEEK_CAPACITY]
        for supply_center in supply_center_set:
            week_capacity_df_in_one_supply_center = week_capacity_df[week_capacity_df[WeekCapacity.SUPPLY_CENTER] == supply_center]
            splited_data_dict[supply_center][TableName.WEEK_CAPACITY] = week_capacity_df_in_one_supply_center

        # 库存现有量
        current_inventory_df = self._data_dict[TableName.CURRENT_INVENTORY]
        for supply_center in supply_center_set:
            current_inventory_df_in_one_supply_center = current_inventory_df[current_inventory_df[CurrentInventory.SUPPLY_CENTER] == supply_center]
            splited_data_dict[supply_center][TableName.CURRENT_INVENTORY] = current_inventory_df_in_one_supply_center

        # 在途PO数据
        intransit_po_df = self._data_dict[TableName.INTRANSIT_PO]
        for supply_center in supply_center_set:
            intransit_po_df_in_one_supply_center = intransit_po_df[intransit_po_df[IntransitPO.SUPPLY_CENTER] == supply_center]
            splited_data_dict[supply_center][TableName.INTRANSIT_PO] = intransit_po_df_in_one_supply_center

        # SOP预测数据
        sop_prediction_df = self._data_dict[TableName.SOP_PREDICTION]
        for supply_center in supply_center_set:
            sop_prediction_df_in_one_supply_center = sop_prediction_df[sop_prediction_df[SOP_PREDICTION.SUPPLY_CENTER] == supply_center]
            splited_data_dict[supply_center][TableName.SOP_PREDICTION] = sop_prediction_df_in_one_supply_center

        self._data_dict = splited_data_dict


    def _filter_valid_skus(self):
        data_dict = self._data_dict

        for supply_center, data in data_dict.items():

            # Step 1: 获取 SKU_MAIN 表中的所有 SKU
            sku_main_df = data[TableName.SKU_MAIN]
            sku_main_skus = set(sku_main_df[SKUMain.SKU])

            # Step 2: 获取 SOP_PREDICTION 表中的所有 SKU
            sop_prediction_df = data[TableName.SOP_PREDICTION]
            sop_prediction_skus = set(sop_prediction_df[SOP_PREDICTION.SKU])

            # Step 3: 获取 WEEK_CAPACITY 表中的所有 PN，并找到对应的 SKU
            week_capacity_df = data[TableName.WEEK_CAPACITY]
            valid_pns = set(week_capacity_df[WeekCapacity.PN])
            valid_skus_from_pn = set(sku_main_df[sku_main_df[SKUMain.PN].isin(valid_pns)][SKUMain.SKU])

            # Step 4: 取三者交集，得到有效 SKU 列表
            valid_skus = sku_main_skus & sop_prediction_skus & valid_skus_from_pn

            # Step 5: 根据有效 SKU 列表，获取有效 PN 集合
            valid_pns_from_skus = set(sku_main_df[sku_main_df[SKUMain.SKU].isin(valid_skus)][SKUMain.PN])

            # Step 6: 过滤数据表格
            current_inventory_df = data[TableName.CURRENT_INVENTORY]
            intransit_po_df = data[TableName.INTRANSIT_PO]
            data[TableName.SKU_MAIN] = sku_main_df[sku_main_df[SKUMain.SKU].isin(valid_skus)]
            data[TableName.SOP_PREDICTION] = sop_prediction_df[sop_prediction_df[SOP_PREDICTION.SKU].isin(valid_skus)]
            data[TableName.WEEK_CAPACITY] = week_capacity_df[week_capacity_df[WeekCapacity.PN].isin(valid_pns_from_skus)]
            data[TableName.CURRENT_INVENTORY] = current_inventory_df[current_inventory_df[CurrentInventory.SKU].isin(valid_skus)]
            data[TableName.INTRANSIT_PO] = intransit_po_df[intransit_po_df[IntransitPO.SKU].isin(valid_skus)]

            self._data_dict[supply_center] = data


    def _fill_MOQ_to_sku_main(self):

        for supply_center, data in self._data_dict.items():
            sku_df = data[TableName.SKU_MAIN]
            # Convert MOQ to numeric, coerce invalid values to NaN, fill NaN with 0, and convert to int
            sku_df.loc[:, SKUMain.MOQ] = pd.to_numeric(sku_df[SKUMain.MOQ], errors='coerce').fillna(0).astype(int)
            data[TableName.SKU_MAIN] = sku_df
            self._data_dict[supply_center] = data

    
    def _merge_current_inventory_into_sku_main(self):
        data_dict = self._data_dict
        for supply_center, data in data_dict.items():
            sku_df = data[TableName.SKU_MAIN]
            current_inventory_df = data[TableName.CURRENT_INVENTORY]
            # Merge current inventory into SKU main data
            merged_df = sku_df.merge(current_inventory_df, left_on=SKUMain.SKU, right_on=CurrentInventory.SKU, how='left')
            merged_df = merged_df.drop(columns=[CurrentInventory.SKU, CurrentInventory.SUPPLY_CENTER])
            # Fill NaN values in quantity with 0
            merged_df[CurrentInventory.QUANTITY] = merged_df[CurrentInventory.QUANTITY].fillna(0)
            merged_df[CurrentInventory.QUANTITY] = merged_df[CurrentInventory.QUANTITY].astype(int)
            data[TableName.CURRENT_INVENTORY] = merged_df
            self._data_dict[supply_center] = data


    def _remove_unmatched_skus_in_po_df(self):
        data_dict = self._data_dict

        for supply_center, data in data_dict.items():
            po_df = data[TableName.INTRANSIT_PO]
            sku_df = data[TableName.SKU_MAIN]

            matched_skus = po_df[IntransitPO.SKU].isin(sku_df[SKUMain.SKU])
            # 过滤不在计划周期内到达的 PO 单
            filtered_po_df = po_df[matched_skus]

            data[TableName.INTRANSIT_PO] = filtered_po_df
            self._data_dict[supply_center] = data


    def _generate_arrival_week_quantity_to_PO_table(self):
        data_dict = self._data_dict

        for supply_center, data in data_dict.items():
            PO_df = data[TableName.INTRANSIT_PO]
            PO_df[IntransitPO.REQUIRED_ARRIVAL_TIME] = pd.to_datetime(PO_df[IntransitPO.REQUIRED_ARRIVAL_TIME])
            PO_df[IntransitPO.REQUIRED_ARRIVAL_WEEK] = PO_df[IntransitPO.REQUIRED_ARRIVAL_TIME].apply(lambda x: self._map_date_to_anker_week(x))
            
            # 过滤不在计划周期内到达的 PO 单
            PO_df = PO_df[PO_df[IntransitPO.REQUIRED_ARRIVAL_WEEK].isin(self._duration)]

            data[TableName.INTRANSIT_PO] = PO_df
            self._data_dict[supply_center] = data


    def _add_model_week_col_to_PO_table(self):
        data_dict = self._data_dict

        for supply_center, data in data_dict.items():
            PO_df = data[TableName.INTRANSIT_PO]
            arrival_anker_weeks = PO_df[IntransitPO.REQUIRED_ARRIVAL_WEEK]
            arrival_model_weeks = self._map_anker_week_to_model_week(arrival_anker_weeks)

            PO_df[IntransitPO.REQUIRED_ARRIVAL_MODEL_WEEK] = arrival_model_weeks
            data[TableName.INTRANSIT_PO] = PO_df
            self._data_dict[supply_center] = data


    def _add_capacity_occupied_week_to_PO_table(self):
        data_dict = self._data_dict

        for supply_center, data in data_dict.items():
            po_df = data[TableName.INTRANSIT_PO]
            po_cols = po_df.columns.tolist()
            sku_df = data[TableName.SKU_MAIN]
            sku_po_merged_df = po_df.merge(sku_df, left_on=IntransitPO.SKU, right_on=SKUMain.SKU, how='left')
            sku_po_merged_df[IntransitPO.CAPACITY_OCCUPIED_MODEL_WEEK] = sku_po_merged_df[IntransitPO.REQUIRED_ARRIVAL_MODEL_WEEK] - sku_po_merged_df[SKUMain.SLA_T] - 1
            po_cols.append(IntransitPO.CAPACITY_OCCUPIED_MODEL_WEEK)
            sku_po_merged_df = sku_po_merged_df[po_cols]
            data[TableName.INTRANSIT_PO] = sku_po_merged_df
            self._data_dict[supply_center] = data


    def _filter_demand_out_of_time_span(self):
        data_dict = self._data_dict

        for supply_center, data in data_dict.items():
            sop_df = data[TableName.SOP_PREDICTION]
            # Filter out demand that is not within the time span
            date_columns = [col for col in sop_df.columns if col.startswith('20') and 'W' in col]
            kept_columns = [col for col in sop_df.columns if col not in date_columns or col in self._duration]
            sop_df = sop_df[kept_columns]

            data[TableName.SOP_PREDICTION] = sop_df
            self._data_dict[supply_center] = data


    def _update_required_inventory_level_to_sop_prediction_table(self):
        data_dict = self._data_dict

        for supply_center, data in data_dict.items():
            sop_df_copy = data[TableName.SOP_PREDICTION].copy()
            sku_df = data[TableName.SKU_MAIN]
            sku_df = sku_df.set_index(SKUMain.SKU)

            week_cols = [col for col in sop_df_copy.columns if col.startswith('20')]
            
            # Calculate required inventory for each SKU
            for sku in sop_df_copy[SOP_PREDICTION.SKU]:
                # Get safety stock weeks for this SKU
                ss_wks = sku_df.loc[sku, SKUMain.SAFTY_STOCK_WEEKS]
                
                # Get demand row for this SKU
                sku_demand = sop_df_copy[sop_df_copy[SOP_PREDICTION.SKU] == sku][week_cols].iloc[0]
                
                # Calculate required inventory for each week
                for i, week in enumerate(week_cols):
                    # Determine how many weeks to sum (considering boundary)
                    weeks_to_sum = min(ss_wks + 1, len(week_cols) - i)
                    
                    # Sum demands for the required weeks
                    required_inv = sku_demand[i: i + weeks_to_sum].sum()
                    
                    # Update result DataFrame
                    sop_df_copy.loc[sop_df_copy[SOP_PREDICTION.SKU] == sku, week] = required_inv

            data[TableName.REQUIRED_INVENTORY_LEVEL] = sop_df_copy
            self._data_dict[supply_center] = data


    def _get_week_string(self, date):
        # 获取 ISO 格式的年份和周数，并格式化为 "YYYYWN" 格式
        year, week, _ = date.isocalendar()
        return f"{year}W{week}"
    

    def _week_to_date(self, week_str):
        # 将 "YYYYWN" 格式转换为日期对象
        year = int(week_str[:4])
        week = int(week_str[5:])
        # 使用当年第一天的日期作为起点
        date = datetime(year, 1, 1)
        # 调整到该年的第N周（ISO周从周一开始）
        delta = timedelta(days=(week-1)*7)
        return date + delta
    

    def _generate_week_schedule(self):
        """
        Example:
            start_week = '2025W50',
            duration = ['2025W50', ..., '2026W23]
        """
        # 将起始周转换为日期
        start_date = self._week_to_date(self._start_week)
        # 生成周期列表
        duration = []
        current_date = start_date
        
        for _ in range(self._time_span):
            week_str = self._get_week_string(current_date)
            duration.append(week_str)
            # 增加7天到下一周
            current_date += timedelta(days=7)
        
        return duration
    
    
    def _generate_real_date_to_anker_week_mapping(self):
        anker_week_mapping = self._data_dict[TableName.ANKER_WEEK]

        anker_week_mapping[AnkerWeek.WEEK] = anker_week_mapping[AnkerWeek.ANKER_WEEK_MONTH_DAY].str.extract(r'(\d{4}W\d+)')
        anker_week_mapping[AnkerWeek.MONTH_AND_DAY] = anker_week_mapping[AnkerWeek.ANKER_WEEK_MONTH_DAY].str.extract(r'(\d{2}/\d{2})')
        anker_week_mapping[AnkerWeek.YEAR] = anker_week_mapping[AnkerWeek.ANKER_MONTH].astype(str).str[:4]
        anker_week_mapping[AnkerWeek.WEEK_START_DATE] = pd.to_datetime(
            anker_week_mapping.apply(lambda x: f"{x['年']}-{x['月/日']}", axis=1), format='%Y-%m/%d'
        )
        anker_week_mapping = anker_week_mapping.sort_values(AnkerWeek.WEEK_START_DATE)

        self._data_dict[TableName.ANKER_WEEK] = anker_week_mapping
        self._anker_week_mapping = anker_week_mapping


    def _map_date_to_anker_week(self, date):
        """
        Convert target date to model date based on start date.
        
        Parameters:
        target_date (pd.Series): Target date(s) in format 'YYYYWn'
        start_date (str): Start date in format 'YYYYWn'
        
        Returns:
        pd.Series: Model date(s) as integer(s), where start_date is model date 1
        """
        anker_week_mapping = self._anker_week_mapping
        for i in range(len(anker_week_mapping) - 1):
            if anker_week_mapping.iloc[i][AnkerWeek.WEEK_START_DATE] <= date < anker_week_mapping.iloc[i + 1][AnkerWeek.WEEK_START_DATE]:
                return anker_week_mapping.iloc[i][AnkerWeek.WEEK]
            
        if date >= anker_week_mapping.iloc[-1][AnkerWeek.WEEK_START_DATE]:
            return pd.NA
        
        return pd.NA
    

    def _map_anker_week_to_model_week(self, weeks: pd.Series):
        plan_start_year_week = self._start_week  # E.g.: "2025W1"

        assert isinstance(weeks, pd.Series)
        start_year, start_week = self._parse_week_string(plan_start_year_week)
        # Handle Series of target dates
        def compute_model_date(t_date):
            target_year, target_week = self._parse_week_string(t_date)
            year_diff = target_year - start_year
            week_diff = target_week - start_week
            total_weeks = year_diff * 52 + week_diff
            return total_weeks + 1
        
        return weeks.apply(compute_model_date)

    
    def _parse_week_string(self, week_str):
        """
        Parse a week string like '2025W2' into year and week number.
        
        Parameters:
        week_str (str): Week string in format 'YYYYWn'
        
        Returns:
        tuple: (year, week) as integers
        """
        match = re.match(r'(\d{4})W(\d+)', week_str)
        if not match:
            raise ValueError(f"Invalid week string format: {week_str}")
        year, week = map(int, match.groups())
        return year, week