import coptpy
from models.MPS_model import MPSModel
from util.data_loader import load_model_params
from util.data_visualizer import DataVisualizer
from util.model_writer import ModelWriter



def main(args, T=26):

    start_week = args["start_week"]
    params = args["solver_params"]
    relax_decision_vars = args["relax_decision_vars"]
    visualize = args["visualize"]

    model_params_cls, _ = load_model_params(start_week, T)

    supply_center_set = model_params_cls.supply_center_set

    # 按 supply_center 求解子问题
    for sc in supply_center_set:
        # 初始化COPT环境
        env = coptpy.Envr()
        # 提取子问题数据
        sub_data = {
            'plan_duration': model_params_cls.T,
            'sku_set': model_params_cls.sku_set[sc],
            'factory_set': model_params_cls.factory_set[sc],
            'SLA_S_dict': model_params_cls.SLA_S_dict[sc],
            'SLA_T_dict': model_params_cls.SLA_T_dict[sc],
            'factory_sku_lists_dict': model_params_cls.factory_sku_lists_dict[sc],
            'capacity_occupancy_dict': model_params_cls.capacity_occupancy_dict[sc],
            'normalized_capacity_dict': model_params_cls.normalized_capacity_dict[sc],
            'MOQ_dict': model_params_cls.MOQ_dict[sc],
            'M': 1e8,
            'week_arrival_quantity_from_PO': model_params_cls.week_arrival_quantity_from_PO[sc],
            'initial_inventory_dict': model_params_cls.initial_inventory_dict[sc],
            'demand_dict': model_params_cls.demand_dict[sc],
            'required_inventory_level_dict': model_params_cls.required_inventory_level_dict[sc],
            'stock_cost_dict': model_params_cls.stock_cost_dict[sc],
            'loss_sales_cost_dict': model_params_cls.loss_sales_cost_dict[sc],
            'available_factory_set_of_skus': model_params_cls.available_factory_set_of_skus[sc],
            'po_capacity_occupation_dicts': model_params_cls.po_capacity_occupation_dicts[sc],
            "isolated_factory_set": model_params_cls.isolated_factory_set[sc]  # NOT be utilized now
        }

        model = MPSModel(env, sc, sub_data, params=params, relax_decision_vars=relax_decision_vars)
        model.solve()

        # 输出求解结果及结果后处理
        model_writer = ModelWriter(model, sc)
        solution_file_path = model_writer.write_solution()
        
        # 可视化库存曲线
        if visualize:
            data_visualizer = DataVisualizer(sc, solution_file_path, sub_data)
            data_visualizer.visualize_all()



if __name__ == "__main__":

    args = {
        "start_week": "2025W1",         # 起始周
        "solver_params": {              # 求解器参数
            'TimeLimit': 300
        }, 
        "relax_decision_vars": True,    # 是否将决策变量放松为连续变量
        "visualize": False              # 是否可视化库存曲线
    }

    main(args)
