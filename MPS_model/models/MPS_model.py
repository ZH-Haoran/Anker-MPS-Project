from coptpy import *
import datetime
import os


class MPSModel:
    """主生产调度问题模型，按 supply_center 划分子问题"""
    def __init__(self, env, supply_center, data, params, relax_decision_vars):
        print(f"Solving for supply center: {supply_center}")
        self.model = self._construct_model(env)
        self._set_params_for_solver(params)
        self.supply_center = supply_center
        self.data = data
        self.sku_set = data['sku_set']
        self.factory_set = data['factory_set']
        self.plan_duration = data['plan_duration']
        self.SLA_S_dict = data['SLA_S_dict']
        self.SLA_T_dict = data['SLA_T_dict']
        self.factory_sku_lists_dict = data['factory_sku_lists_dict']
        self.capacity_occupancy_dict = data['capacity_occupancy_dict']
        self.normalized_capacity_dict = data['normalized_capacity_dict']
        self.MOQ_dict = data['MOQ_dict']
        self.intransit_PO_dict = data.get('week_arrival_quantity_from_PO', {})
        self.initial_inventory_dict = data['initial_inventory_dict']
        self.demand_dict = data['demand_dict']
        self.required_inventory_level_dict = data['required_inventory_level_dict']
        self.stock_cost_dict = data['stock_cost_dict']
        self.loss_sales_cost_dict = data['loss_sales_cost_dict']
        self.available_factory_set_of_skus = data['available_factory_set_of_skus']
        self.po_capacity_occupation_dicts = data['po_capacity_occupation_dicts']
        self.M = data['M']

        self.relax_decision_vars = relax_decision_vars
        self.variables = {}


    def solve(self):
        self._add_variables()
        self._add_constraints()
        self._set_objective()
        self._save_model()
        self.model.solve()


    def _set_params_for_solver(self, params):
        for param, value in params.items():
            self.model.setParam(param, value)


    def _save_model(self):
        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(f"./mps/supply_center_{self.supply_center}", exist_ok=True)
        mps_file_name = f"./mps/supply_center_{self.supply_center}/mps_model_{current_time}.mps"
        self.model.write(mps_file_name)
        print(f".mps model file has been saved to {mps_file_name}")


    def _construct_model(self, env):
        model = env.createModel("Master Production Scheduling")
        return model


    def _add_variables(self):
        """添加决策变量"""
        self._add_order_decision_vars()
        self._add_order_indicator_vars()
        self._add_demand_statisfied_indicator_vars()
        self._add_inventory_vars()
        self._add_stockout_vars()
        self._add_slack_vars_for_required_inventory_level()

        print(f"Added {len(self.variables)} variables for {self.supply_center}")


    def _add_constraints(self):
        """添加约束条件"""
        self._add_capacity_constraints()
        self._add_moq_constraints()
        self._add_inventory_balance_constraints()
        self._add_demand_satisfaction_constraints()
        self._add_required_inventory_constraints()

        print(f"Added constraints for {self.supply_center}")


    def _set_objective(self):
        """设置目标函数"""
        obj = quicksum(
            quicksum(self.stock_cost_dict[p_code] * self.variables['inventory_vars'][f"I_{p_code}_{t}"] for t in range(self.plan_duration)) +
            quicksum(self.loss_sales_cost_dict[p_code] * self.variables['stockout_vars'][f"u_{p_code}_{t}"] for t in range(int(self.SLA_S_dict[p_code]), self.plan_duration)) +
            quicksum(5 * self.variables['slack_vars'][f"s_{p_code}_{t}"] for t in range(int(self.SLA_S_dict[p_code]), self.plan_duration))
            for p, p_code in enumerate(self.sku_set)
        )

        self.model.setObjective(obj, sense=COPT.MINIMIZE)
        print(f"Objective function set for {self.supply_center}")


    def _add_order_decision_vars(self):
        """添加订单决策变量"""
        var_type = 'order_decision_vars'
        self.variables[var_type] = {}
        for f in self.factory_set:
            for p in self.factory_sku_lists_dict[f]:
                if self.plan_duration - int(self.SLA_S_dict[p]) <= 0:
                    print(f"Warning! {p} will NOT be included in this plan since its supply SLA {self.SLA_S_dict[p]} >= plan duration {self.plan_duration}")
                else:
                    for t in range(self.plan_duration - int(self.SLA_S_dict[p])):
                        var_name = f"x_{f}_{p}_{t}"
                        if self.relax_decision_vars:
                            self.variables[var_type][var_name] = self.model.addVar(vtype=COPT.CONTINUOUS, name=var_name, lb=0)
                        else:
                            self.variables[var_type][var_name] = self.model.addVar(vtype=COPT.INTEGER, name=var_name, lb=0)


    def _add_order_indicator_vars(self):
        """添加订单指示变量"""
        var_type = 'order_indicator_vars'
        self.variables[var_type] = {}
        for f in self.factory_set:
            for p in self.factory_sku_lists_dict[f]:
                q = self.MOQ_dict[p]
                if q > 0:
                    for t in range(self.plan_duration - int(self.SLA_S_dict[p])):
                        var_name = f"z_{f}_{p}_{t}"
                        self.variables[var_type][var_name] = self.model.addVar(vtype=COPT.BINARY, name=var_name)


    def _add_demand_statisfied_indicator_vars(self):
        """添加需求满足指示变量"""
        var_type = 'demand_statisfied_indicator_vars'
        self.variables[var_type] = {}
        for p in self.sku_set:
            for t in range(self.plan_duration):
                var_name = f"e_{p}_{t}"
                self.variables[var_type][var_name] = self.model.addVar(vtype=COPT.BINARY, name=var_name)


    def _add_inventory_vars(self):
        """添加库存变量"""
        var_type = 'inventory_vars'
        self.variables[var_type] = {}
        for p in self.sku_set:
            for t in range(self.plan_duration):
                var_name = f"I_{p}_{t}"
                self.variables[var_type][var_name] = self.model.addVar(vtype=COPT.CONTINUOUS, name=var_name, lb=0)


    def _add_stockout_vars(self):
        """添加缺货变量"""
        var_type = 'stockout_vars'
        self.variables[var_type] = {}
        for p in self.sku_set:
            for t in range(self.plan_duration):
                var_name = f"u_{p}_{t}"
                self.variables[var_type][var_name] = self.model.addVar(vtype=COPT.CONTINUOUS, name=var_name, lb=0)


    def _add_slack_vars_for_required_inventory_level(self):
        """添加要求库存水平的松弛变量"""
        var_type = 'slack_vars'
        self.variables[var_type] = {}
        for p in self.sku_set:
            for t in range(int(self.SLA_S_dict[p]), self.plan_duration):
                var_name = f"s_{p}_{t}"
                self.variables[var_type][var_name] = self.model.addVar(vtype=COPT.CONTINUOUS, name=var_name, lb=0)


    def _add_capacity_constraints(self):
        """添加产能约束"""
        for f in self.factory_set:
            for t in range(self.plan_duration):
                lhs = 0.0
                for p in self.factory_sku_lists_dict[f]:
                    for tau in range(self.plan_duration - int(self.SLA_S_dict[p])):
                        if tau + self.SLA_S_dict[p] - self.SLA_T_dict[p] - 1 == t:
                            coeff = self.capacity_occupancy_dict[f][p][t]
                            order_decision_var = self.variables['order_decision_vars'][f"x_{f}_{p}_{tau}"]
                            lhs += order_decision_var * coeff
                normalized_capacity = self.normalized_capacity_dict[f][t]
                po_capacity_occupation = self.po_capacity_occupation_dicts[f][t] if f in self.po_capacity_occupation_dicts.keys() else 0
                remaining_capacity = normalized_capacity - po_capacity_occupation if normalized_capacity - po_capacity_occupation > 0 else 0
                self.model.addConstr(lhs <= remaining_capacity, name=f"Capacity_{f}_{t}")


    def _add_moq_constraints(self):
        """添加最小下单量约束"""
        for f in self.factory_set:
            for p in self.factory_sku_lists_dict[f]:
                for t in range(self.plan_duration - int(self.SLA_S_dict[p])):
                    q = self.MOQ_dict[p]  # 获取 MOQ 值
                    if q > 0:
                        order_decision_var = self.variables['order_decision_vars'][f"x_{f}_{p}_{t}"]
                        order_indicator_var = self.variables['order_indicator_vars'][f"z_{f}_{p}_{t}"]
                        
                        # 添加约束：订单量 >= MOQ * 订单指示变量
                        self.model.addConstr(order_decision_var >= q * order_indicator_var, name=f"MOQ_{f}_{p}_{t}")
                        
                        # 添加约束：订单量 <= M * 订单指示变量
                        self.model.addConstr(order_decision_var <= self.M * order_indicator_var, name=f"OrderIndicator_{f}_{p}_{t}")


    def _add_inventory_balance_constraints(self):
        """添加库存平衡约束"""
        for p in self.sku_set:
            for t in range(self.plan_duration):
                sum_prod = 0
                if t >= int(self.SLA_S_dict[p]):
                    for f in self.available_factory_set_of_skus[p]:
                        tau = int(t - self.SLA_S_dict[p])
                        order_decision_var = self.variables['order_decision_vars'][f"x_{f}_{p}_{tau}"]
                        sum_prod += order_decision_var
                
                inventory_var = self.variables['inventory_vars'][f"I_{p}_{t}"]
                stockout_var = self.variables['stockout_vars'][f"u_{p}_{t}"]
                
                if t == 0:
                    # 初始库存约束
                    initial_inventory = self.initial_inventory_dict.get(p, 0)
                    intransit_po = self.intransit_PO_dict.get(p, {})[t]
                    demand = self.demand_dict.get(p, {})[t]
                    
                    self.model.addConstr(
                        inventory_var == initial_inventory + intransit_po - demand + stockout_var,
                        name=f"Inventory_{p}_{t}"
                    )
                else:
                    # 后续时间段的库存约束
                    prev_inventory_var = self.variables['inventory_vars'][f"I_{p}_{t - 1}"]
                    intransit_po = self.intransit_PO_dict.get(p, {})[t]
                    demand = self.demand_dict.get(p, {})[t]
                    
                    self.model.addConstr(
                        inventory_var == prev_inventory_var + sum_prod + intransit_po - demand + stockout_var,
                        name=f"Inventory_{p}_{t}"
                    )


    def _add_demand_satisfaction_constraints(self):
        """添加辅助库存平衡约束（确保每周的可用库存都用于满足需求）"""
        for p in self.sku_set:
            for t in range(self.plan_duration):
                demand_satisfied_indicator = self.variables['demand_statisfied_indicator_vars'][f"e_{p}_{t}"]
                inventory_var = self.variables['inventory_vars'][f"I_{p}_{t}"]
                stockout_var = self.variables['stockout_vars'][f"u_{p}_{t}"]

                self.model.addConstr(
                    stockout_var <= self.M * (1 - demand_satisfied_indicator),
                    name=f"DemandSatisfaction_{p}_{t}_1"
                )
                self.model.addConstr(
                    inventory_var <= self.M * demand_satisfied_indicator,
                    name=f"DemandSatisfaction_{p}_{t}_2"
                )
    

    def _add_required_inventory_constraints(self):
        """添加目标库存水平约束"""
        for p in self.sku_set:
            for t in range(int(self.SLA_S_dict[p]), self.plan_duration):
                sum_prod = 0
                for f in self.available_factory_set_of_skus[p]:
                    tau = int(t - self.SLA_S_dict[p])
                    order_decision_var = self.variables['order_decision_vars'][f"x_{f}_{p}_{tau}"]
                    sum_prod += order_decision_var
                
                required_inventory_level = self.required_inventory_level_dict.get(p, {})[t]
                prev_inventory_var = self.variables['inventory_vars'][f"I_{p}_{t - 1}"] if t > 0 else self.initial_inventory_dict.get(p, 0)
                po_arrival = self.intransit_PO_dict.get(p, {})[t]
                total_inventory = prev_inventory_var + sum_prod + po_arrival
                slack_var = self.variables['slack_vars'][f"s_{p}_{t}"]

                self.model.addConstr(
                    total_inventory >= required_inventory_level - slack_var,
                    name=f"Required_inventory_{p}_{t}"
                )
                