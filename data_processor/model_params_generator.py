from typing import Dict, List

from util.header import *
import numpy as np


class ModelParams:
    def __init__(self, data_dict, T):
        _model_params_generator = ModelParamsGenerator(data_dict)

        self.T = T
        self.supply_center_set = list(data_dict.keys())
        self.sku_set = _model_params_generator.generate_sku_set()
        self.factory_set = _model_params_generator.generate_factory_set()
        self.bg_to_sku_mapping_dict = _model_params_generator.generate_bg_to_sku_mapping_dict()
        self.available_factory_set_of_skus = _model_params_generator.generate_available_factory_set_of_skus()
        self.factory_sku_lists_dict = _model_params_generator.generate_factory_sku_lists_dict()
        self.SLA_S_dict = _model_params_generator.generate_SLA_S_dict()
        self.stock_cost_dict = _model_params_generator.generate_stock_cost_dict()
        self.loss_sales_cost_dict = _model_params_generator.generate_loss_sales_cost_dict()
        self.MOQ_dict = _model_params_generator.generate_MOQ_dict()
        self.SLA_T_dict = _model_params_generator.generate_SLA_T_dict()
        self.initial_inventory_dict = _model_params_generator.generate_initial_inventory_dict()
        self.demand_dict = _model_params_generator.generate_demand_dict()
        self.required_inventory_level_dict = _model_params_generator.generate_required_inventory_level_dict()
        self.isolated_factory_set = _model_params_generator.generate_isolated_sku_set()  # generate one-to-one skus-sp pairs dict{factory: list(skus)}
        self.normalized_capacity_dict, self.capacity_occupancy_dict = _model_params_generator.generate_normalized_capacity_and_capacity_occupancy()
        self.week_arrival_quantity_from_PO = _model_params_generator.generate_week_arrival_quantity_from_PO(T, self.sku_set)
        self.po_capacity_occupation_dicts = _model_params_generator.generate_po_capacity_occupation(self.capacity_occupancy_dict, T)


class ModelParamsGenerator:
    def __init__(self, data_dict: Dict):
        self._data_dict = data_dict


    def generate_sku_set(self):
        data_dict = self._data_dict

        sku_set = {
            supply_center: data[TableName.SKU_MAIN][SKUMain.SKU].unique().tolist()
            for supply_center, data in data_dict.items()
        }

        return sku_set
    

    def generate_factory_set(self):
        data_dict = self._data_dict

        factory_set = {
            supply_center: data[TableName.WEEK_CAPACITY][WeekCapacity.FACTORY].unique().tolist()
            for supply_center, data in data_dict.items()
        }

        return factory_set
    

    def generate_available_factory_set_of_skus(self):
        data_dict = self._data_dict

        available_factory_set_of_skus = {}
        for supply_center, data in data_dict.items():
            sku_df = data[TableName.SKU_MAIN]
            capacity_df = data[TableName.WEEK_CAPACITY]

            # 从SKUMain表格中获取SKU和PN的映射
            sku_pn_mapping = sku_df[[SKUMain.SKU, SKUMain.PN]].drop_duplicates()
            
            # 从产能表中获取PN和组装厂的映射
            pn_factory_mapping = capacity_df[[WeekCapacity.PN, WeekCapacity.FACTORY]]
            
            # 合并两个映射：通过PN关联SKU和组装厂
            sku_factory_df = sku_pn_mapping.merge(pn_factory_mapping, left_on=SKUMain.PN, right_on=WeekCapacity.PN, how='left')
            
            # 按SKU分组，收集每个SKU对应的所有工厂
            sku_factory_dict = {}
            for sku, group in sku_factory_df.groupby(SKUMain.SKU):
                factories = group[WeekCapacity.FACTORY].dropna().unique().tolist()
                sku_factory_dict[sku] = factories if factories else []

            available_factory_set_of_skus[supply_center] = sku_factory_dict

        return available_factory_set_of_skus
    

    def generate_factory_sku_lists_dict(self):
        """
        Generate a dictionary mapping each factory to a list of SKUs it can produce.
        
        Returns:
        - dict: Dictionary where keys are factory and values are lists of SKUs.
        """
        data_dict = self._data_dict
        factory_sku_lists_dict = {}
        for supply_center, data in data_dict.items():
            sku_df = data[TableName.SKU_MAIN]
            capacity_df = data[TableName.WEEK_CAPACITY]

            factory_sku_lists = {}
            # Get SKU-to-PN mapping from SKU_MAIN table
            sku_pn_mapping = sku_df[[SKUMain.SKU, SKUMain.PN]].drop_duplicates()

            # Get PN-to-factory mapping from WEEK_CAPACITY table
            pn_factory_mapping = capacity_df[[WeekCapacity.PN, WeekCapacity.FACTORY]].drop_duplicates()

            # Merge mappings to link SKUs to factories via PN
            sku_factory_df = sku_pn_mapping.merge(
                pn_factory_mapping,
                left_on=SKUMain.PN,
                right_on=WeekCapacity.PN,
                how='left'
            )

            # Group by factory to collect SKUs
            for factory, group in sku_factory_df.groupby(WeekCapacity.FACTORY):
                skus = group[SKUMain.SKU].dropna().unique().tolist()
                if factory not in factory_sku_lists:
                    factory_sku_lists[factory] = []
                factory_sku_lists[factory].extend(skus)

            factory_sku_lists_dict[supply_center] = factory_sku_lists
            
            # Handle SKUs with no factory (optional debugging)
            no_factory_skus = sku_factory_df[sku_factory_df[WeekCapacity.FACTORY].isna()][SKUMain.SKU].unique()
            if len(no_factory_skus) > 0:
                print(f"Supply Center {supply_center}: {len(no_factory_skus)} SKUs with no factory: {no_factory_skus.tolist()}")

        # Remove duplicates in each factory's SKU list and sort for consistency
        for factory in factory_sku_lists:
            factory_sku_lists[factory] = sorted(list(set(factory_sku_lists[factory])))

        return factory_sku_lists_dict


    def generate_bg_to_sku_mapping_dict(self) -> Dict:
        data_dict = self._data_dict

        bg_to_sku_mapping_dict = { supply_center: {
            bg: group[SKUMain.SKU].tolist()
            for bg, group in data[TableName.SKU_MAIN].groupby(SKUMain.BG)} 
        for supply_center, data in data_dict.items() }
        
        return bg_to_sku_mapping_dict
    

    def generate_SLA_S_dict(self) -> Dict:
        data_dict = self._data_dict

        sla_s_dict = {}
        for supply_center, data in data_dict.items():
            sku_data = data[TableName.SKU_MAIN]
            sla_s_dict[supply_center] = dict(zip(sku_data[SKUMain.SKU].tolist(), sku_data[SKUMain.SLA_S].tolist()))

        return sla_s_dict
    

    def generate_stock_cost_dict(self) -> Dict:
        data_dict = self._data_dict

        stock_cost_dict = {}
        for supply_center, data in data_dict.items():
            sku_data = data[TableName.SKU_MAIN]
            stock_cost_dict[supply_center] = dict(zip(sku_data[SKUMain.SKU].tolist(), sku_data[SKUMain.STOCK_OUT_COST].tolist()))

        return stock_cost_dict
    

    def generate_loss_sales_cost_dict(self) -> Dict:
        data_dict = self._data_dict

        loss_sales_cost_dict = {}
        for supply_center, data in data_dict.items():
            sku_data = data[TableName.SKU_MAIN]
            loss_sales_cost_dict[supply_center] = dict(zip(sku_data[SKUMain.SKU].tolist(), sku_data[SKUMain.LOSS_SALES_COST].tolist()))

        return loss_sales_cost_dict
    

    def generate_MOQ_dict(self) -> Dict:
        data_dict = self._data_dict

        moq_dict = {}
        for supply_center, data in data_dict.items():
            sku_data = data[TableName.SKU_MAIN]
            moq_dict[supply_center] = dict(zip(sku_data[SKUMain.SKU].tolist(), sku_data[SKUMain.MOQ].tolist()))

        return moq_dict
    

    def generate_SLA_T_dict(self) -> Dict:
        data_dict = self._data_dict

        sla_t_dict = {}
        for supply_center, data in data_dict.items():
            sku_data = data[TableName.SKU_MAIN]
            sla_t_dict[supply_center] = dict(zip(sku_data[SKUMain.SKU].tolist(), sku_data[SKUMain.SLA_T].tolist()))

        return sla_t_dict
    

    def generate_initial_inventory_dict(self) -> Dict:
        data_dict = self._data_dict

        initial_inventory_dict = {}
        for supply_center, data in data_dict.items():
            initial_inventory_data = data[TableName.CURRENT_INVENTORY]
            initial_inventory_dict[supply_center] = dict(
                zip(initial_inventory_data[SKUMain.SKU].tolist(), initial_inventory_data[CurrentInventory.QUANTITY].tolist())
                )

        return initial_inventory_dict
    

    def generate_demand_dict(self):
        data_dict = self._data_dict

        demand_dicts = {}
        for supply_center, data in data_dict.items():
            demand_data = data[TableName.SOP_PREDICTION]

            week_cols = [col for col in demand_data.columns if col.startswith('20')]
            demand_dict = {}
            for _, row in demand_data.iterrows():
                sku = row[SOP_PREDICTION.SKU]
                weekly_demand = row[week_cols].tolist()
                demand_dict[sku] = weekly_demand

            demand_dicts[supply_center] = demand_dict

        return demand_dicts
    

    def generate_required_inventory_level_dict(self) -> Dict:
        data_dict = self._data_dict

        required_inventory_level_dict = {}
        for supply_center, data in data_dict.items():
            required_inventory_level_data = data[TableName.REQUIRED_INVENTORY_LEVEL]

            week_cols = [col for col in required_inventory_level_data.columns if col.startswith('20')]
            inventory_dict = {}
            for _, row in required_inventory_level_data.iterrows():
                sku = row[RequiredInventoryLevel.SKU]
                weekly_inventory = row[week_cols].tolist()
                inventory_dict[sku] = weekly_inventory

            required_inventory_level_dict[supply_center] = inventory_dict

        return required_inventory_level_dict

    
    def generate_isolated_sku_set(self):
        data_dict = self._data_dict

        isolated_factory_set = {}
        for supply_center, data in data_dict.items():
            print('Current supply center:', supply_center)
            sku_data = data[TableName.SKU_MAIN]
            capacity_data = data[TableName.WEEK_CAPACITY]

            pn_to_sku_dict = {}
            for pn, group in sku_data.groupby(SKUMain.PN):
                pn_to_sku_dict[pn] = group[SKUMain.SKU].tolist()

            pn_to_factory = {}  # pn -> set of factory
            factory_to_pn = {}  # factory -> set of pn
            for _, row in capacity_data.iterrows():
                pn = row[WeekCapacity.PN]
                factory = row[WeekCapacity.FACTORY]

                if pn not in pn_to_factory:
                    pn_to_factory[pn] = set()
                pn_to_factory[pn].add(factory)
                
                if factory not in factory_to_pn:
                    factory_to_pn[factory] = set()
                factory_to_pn[factory].add(pn)

            factory_in_one_to_one_pairs = {}
            # sku_in_one_to_one_pairs = []
            for f, pn_set in factory_to_pn.items():
                if len(pn_set) == 1:  # 这个 factory 只对应一个pn
                    pn = list(pn_set)[0]
                    if len(pn_to_factory[pn]) == 1:  # 这个pn也只对应一个 factory
                        # factory_in_one_to_one_pairs.append(f)
                        factory_in_one_to_one_pairs[f] = [sku for sku in pn_to_sku_dict[pn] if pn in pn_to_sku_dict]

            # isolated_sku_set[supply_center] = sku_in_one_to_one_pairs
            isolated_factory_set[supply_center] = factory_in_one_to_one_pairs

        return isolated_factory_set
    

    def generate_normalized_capacity_and_capacity_occupancy(self):
        """
        Calculate factory standard capacity and unit capacity usage from capacity DataFrame.
        
        Parameters:
        capacity_df (pd.DataFrame): DataFrame with capacity data, columns include factories, SKUs, weeks, and capacities
        
        Returns:
        tuple: (dict, dict)
            - Factory standard capacity: {factory: list of capacities for each week}
            - Unit capacity usage: {factory: {sku: list of usage for each week}}
        """
        # Retrieve data dictionary
        data_dict = self._data_dict

        # Initialize dictionaries to store results
        factory_standard_capacities = {}  # {supply_center: {factory: list of capacities}}
        sku_capacity_usage = {}  # {supply_center: {factory: {sku: list of usage}}}

        for supply_center, datasets in data_dict.items():
            # Extract capacity and SKU data
            capacity_data = datasets[TableName.WEEK_CAPACITY]
            sku_data = datasets[TableName.SKU_MAIN]

            # Identify week columns (starting with '20')
            week_columns = [col for col in capacity_data.columns if col.startswith('20')]

            # Build PN to SKU mapping
            # TODO: can be optimized
            pn_to_sku_mapping = {}
            for pn, group in sku_data.groupby(SKUMain.PN):
                pn_to_sku_mapping[pn] = group[SKUMain.SKU].tolist()

            # Initialize dictionaries for this supply center
            factory_capacities = {}  # {factory: list of C_{f, t}}
            factory_sku_usage = {}  # {factory: {sku: list of o_{f, p, t}}}

            # Group capacity data by factory
            capacity_by_factory = capacity_data.groupby(WeekCapacity.FACTORY)

            for factory, factory_group in capacity_by_factory:
                # Extract capacity matrix for this factory
                capacity_values = factory_group[week_columns].values  # Shape: (num_pns, num_weeks)

                # 1. Calculate factory standard capacity C_{f, t} = max_p C_{f, p, t}
                standard_capacity = np.max(capacity_values, axis=0).tolist()
                factory_capacities[factory] = standard_capacity

                # 2. Calculate unit capacity usage o_{f, p, t} = C_{f, t} / C_{f, p, t}
                part_numbers = factory_group[WeekCapacity.PN].values  # PN list for this factory
                sku_usage = {}  # {sku: list of usage}

                for pn_index, part_number in enumerate(part_numbers):
                    # Map PN to SKUs
                    skus_for_pn = pn_to_sku_mapping.get(part_number, [])
                    if not skus_for_pn:  # Skip if PN has no corresponding SKUs
                        continue

                    # Get capacity for this PN
                    pn_capacity = capacity_values[pn_index]  # C_{f, p, t} for this PN

                    # Calculate usage for each SKU mapped to this PN
                    for sku in skus_for_pn:
                        usage_per_week = []
                        for week_index, factory_capacity in enumerate(standard_capacity):
                            pn_week_capacity = pn_capacity[week_index]
                            if pn_week_capacity == 0:
                                # Handle division by zero: use a large value (e.g., 1e8)
                                usage_per_week.append(1e8)
                            else:
                                usage_per_week.append(float(factory_capacity / pn_week_capacity))

                        sku_usage[sku] = usage_per_week

                factory_sku_usage[factory] = sku_usage

            # Store results for this supply center
            factory_standard_capacities[supply_center] = factory_capacities
            sku_capacity_usage[supply_center] = factory_sku_usage

        return factory_standard_capacities, sku_capacity_usage
    

    def generate_week_arrival_quantity_from_PO(self, T, sku_set):
        """
        Generate a dictionary from arrival DataFrame where key is SKU and value is a list of arrival quantities
        for each model week. If no arrival for a model week, set quantity to 0.
        
        Returns:
        dict: Dictionary with SKU as key and list of arrival quantities (length T) as value
        """
        data_dict = self._data_dict

        week_arrival_quantity_dicts = {}
        for supply_center, data in data_dict.items():
            PO_df = data[TableName.INTRANSIT_PO]

            # Group by SKU and model week, summing quantities
            grouped = PO_df.groupby(
                [IntransitPO.SKU, IntransitPO.REQUIRED_ARRIVAL_MODEL_WEEK]
                )[IntransitPO.INTRANSIT_QUANTITY].sum().reset_index()
            
            # Initialize the dictionary
            sku_dict = {}
            
            # For each SKU, create a list of quantities
            for sku in sku_set[supply_center]:
                # Filter rows for this SKU
                sku_data = grouped[grouped[IntransitPO.SKU] == sku]
                
                # Initialize list with zeros for all weeks
                quantities = [0.0] * T
                
                # Fill in quantities for the weeks where data exists
                for _, row in sku_data.iterrows():
                    week_idx = int(row[IntransitPO.REQUIRED_ARRIVAL_MODEL_WEEK]) - 1  # Convert to 0-based index
                    quantities[week_idx] = row[IntransitPO.INTRANSIT_QUANTITY]
                
                sku_dict[sku] = quantities

            week_arrival_quantity_dicts[supply_center] = sku_dict

        return week_arrival_quantity_dicts
    

    def generate_po_capacity_occupation(self, unit_capacity: Dict[str, List[float]], T: int) -> Dict[str, List[float]]:
        """
        生成在途PO订单对产能占用量的字典。
            
        Returns:
            Dict[str, List[float]]，格式为 {factory: [产能占用 for t in range(T)]}
        """

        data_dict = self._data_dict

        po_capacity_occupation_dicts = {}
        for supply_center, data in data_dict.items():
            unit_capacity_df = unit_capacity[supply_center]
            # Initialize the output dictionary
            capacity_occupation_dicts = {}
            po_df = data[TableName.INTRANSIT_PO]
            po_df = po_df[po_df[IntransitPO.CAPACITY_OCCUPIED_MODEL_WEEK] >= 1]
            factory_set = po_df[IntransitPO.SUPPLIER].unique().tolist()
            # Group by factory, SKU, and model week, summing quantities
            grouped = po_df.groupby(
                [IntransitPO.SUPPLIER, IntransitPO.SKU, IntransitPO.CAPACITY_OCCUPIED_MODEL_WEEK]
            )[IntransitPO.INTRANSIT_QUANTITY].sum().reset_index()
            
            # Process each factory
            for factory in factory_set:
                # Initialize dictionary for this factory
                capacity_dict = [0.0] * T
                
                # Filter rows for this factory
                factory_data = grouped[grouped[IntransitPO.SUPPLIER] == factory]
                
                # Calculate capacity occupation for each SKU and week
                for _, row in factory_data.iterrows():
                    sku = row[IntransitPO.SKU]
                    week_idx = int(row[IntransitPO.CAPACITY_OCCUPIED_MODEL_WEEK]) - 1  # Convert to 0-based index
                    quantity = int(row[IntransitPO.INTRANSIT_QUANTITY])
                    
                    # Ensure week_idx is within valid range and SKU is in unit_capacity
                    if factory in unit_capacity_df.keys() and sku in unit_capacity_df[factory].keys():
                        # Calculate capacity occupation = quantity * unit capacity
                        unit_cap = unit_capacity_df[factory][sku][week_idx]
                        capacity_dict[week_idx] += quantity * unit_cap
                
                capacity_occupation_dicts[factory] = capacity_dict

            po_capacity_occupation_dicts[supply_center] = capacity_occupation_dicts
            
        return po_capacity_occupation_dicts
                            