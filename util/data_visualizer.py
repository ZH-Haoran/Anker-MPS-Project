import os
import re
import matplotlib.pyplot as plt
from typing import Dict


class DataVisualizer:
    def __init__(self, supply_center: str, input_file: str,  data: Dict, selected_skus=None):

        self.supply_center = supply_center
        self.input_file = input_file
        self.selected_skus = selected_skus
        self.data = data
        self.plan_duration = data['plan_duration']
        
        # 解析.sol文件
        self.sol_data = self._parse_sol_file()
        
        # 创建可视化目录
        self.save_path = f"./visualization/supply_center_{self.supply_center}"
        os.makedirs(self.save_path, exist_ok=True)
    
    
    def _parse_sol_file(self) -> Dict:
        
        sol_data = {
            'orders': {},
            'inventory': {},
            'shortage': {},
            'stock_violation': {}
        }

        # 新正则匹配：x_工厂ID_SKU编号_周数
        order_pattern = re.compile(r'^x_([A-Z0-9]+)_(SKU\d+)_(\d+)\s+([-]?\d+)')
        # 其他变量模式保持不变
        other_pattern = re.compile(r'^([Ius])_(SKU\d+)_(\d+)\s+([-]?\d+)')

        with open(self.input_file, 'r') as f:
            next(f)  # 跳过第一行
            
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # 优先尝试匹配订单模式（包含工厂信息）
                order_match = order_pattern.match(line)
                if order_match:
                    factory, sku, week, qty = order_match.groups()
                    week = int(week)
                    qty = int(qty)
                    
                    if sku not in sol_data['orders']:
                        sol_data['orders'][sku] = {}
                    if factory not in sol_data['orders'][sku]:
                        sol_data['orders'][sku][factory] = []
                    sol_data['orders'][sku][factory].append(qty)
                    continue
                    
                # 匹配其他变量
                other_match = other_pattern.match(line)
                if other_match:
                    var_type, sku, week, value = other_match.groups()
                    week = int(week)
                    value = int(value)
                    
                    if var_type == 'I':
                        if sku not in sol_data['inventory']:
                            sol_data['inventory'][sku] = []
                        sol_data['inventory'][sku].append(value)
                    elif var_type == 'u':
                        if sku not in sol_data['shortage']:
                            sol_data['shortage'][sku] = []
                        sol_data['shortage'][sku].append(value)
                    elif var_type == 's':
                        if sku not in sol_data['stock_violation']:
                            sol_data['stock_violation'][sku] = []
                        sol_data['stock_violation'][sku].append(value)            

        return sol_data
    
    
    def _plot_inventory_curves(self):
        """
        为选定的SKU绘制库存变化曲线和要求库存曲线
        """
        print("Visualizing ...")
        if self.selected_skus is None:
            self.selected_skus = self.data['sku_set']

        for sku in self.selected_skus:
            # 获取初始库存数据
            initial_inventory_data = self.data['initial_inventory_dict'].get(sku, 0)

            # 获取库存数据
            inventory_data = self.sol_data['inventory'].get(sku, [])
            if not inventory_data:
                print(f"Warning: No inventory data found for {sku}")
                continue
            
            # 获取要求库存数据
            required_inventory = self.data.get('required_inventory_level_dict', {}).get(sku, [])
            if not required_inventory:
                print(f"Warning: No required inventory data found for {sku}")
                continue

            # 获取需求数据
            demand = self.data.get('demand_dict', {}).get(sku, [])
            if not demand:
                print(f"Warning: No demand data found for {sku}")
                continue

            # 获取 PO 单到达数据
            po_arrival = self.data['po_capacity_occupation_dicts'].get(sku, [0 for _ in range(self.plan_duration)])
            assert len(po_arrival) == self.plan_duration

            # 获取下单数据
            orders = self.sol_data['orders'].get(sku, [])
            total_orders_of_sku_in_each_week = [sum(x) for x in zip(*orders.values())] if isinstance(orders, dict) else [0 for _ in range(self.plan_duration)]
            total_orders_of_sku_in_each_week = [0 for _ in range(int(self.data['SLA_S_dict'][sku]))] + total_orders_of_sku_in_each_week
            total_orders_of_sku_in_each_week = total_orders_of_sku_in_each_week[:self.plan_duration]
            assert len(total_orders_of_sku_in_each_week) == self.plan_duration

            # 计算各周库存
            actual_inventory = []
            for week in range(self.plan_duration):
                prev_inventory = inventory_data[week - 1] if week > 0 else initial_inventory_data
                inventory = prev_inventory + po_arrival[week] + total_orders_of_sku_in_each_week[week]
                actual_inventory.append(inventory)
            
            # 准备绘图数据
            total_weeks = [i for i in range(self.plan_duration)]
            
            # 绘制曲线
            plt.figure(figsize=(10, 6))
            plt.plot(total_weeks, actual_inventory, label='Actual Inventory', marker='o')
            plt.plot(total_weeks, required_inventory, label='Required Inventory', marker='x')
            plt.plot(total_weeks, demand, label='Demand', marker='s')
            plt.plot(total_weeks, total_orders_of_sku_in_each_week, label='arrived orders', marker='^', color='y', alpha=0.5)
            plt.axvline(x=int(self.data['SLA_S_dict'][sku]), color='red', linestyle='--', label='SLA S')
            
            plt.title(f"Inventory Curves for {sku}")
            plt.xlabel("Week")
            plt.ylabel("Quantity")
            plt.legend()
            plt.grid(True)
            
            # 保存图像
            plt.savefig(os.path.join(self.save_path, f"{sku}_inventory_curves.png"))
            plt.close()

        print(f"All figures have been saved to {self.save_path}")


    def visualize_all(self):
        """
        执行所有可视化任务
        """
        self._plot_inventory_curves()
