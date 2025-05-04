import datetime
import os

class ModelWriter:
    def __init__(self, mps_model, supply_center):
        self.model = mps_model.model
        self.supply_center = supply_center


    def write_solution(self):
        """将求解结果写入文件"""
        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        os.makedirs(f"output/MPS/supply_center_{self.supply_center}", exist_ok=True)
        file_name = f"output/MPS/supply_center_{self.supply_center}/mps_model_{current_time}.sol"

        self.model.write(file_name)
        print(f"Solution written to {file_name}")

        filtered_file_name = self._filter_zero_vars_out(file_name)
        print(f"Filtered solution written to {filtered_file_name}")
        
        return file_name  # return the whole solution file path for visualization


    def _filter_zero_vars_out(self, file_name):

        filtered_file_name = file_name.replace('.sol', '_filtered.sol')
        with open(file_name, 'r') as f_in, open(filtered_file_name, 'w') as f_out:
            # 保留第一行（目标值）
            first_line = f_in.readline()
            f_out.write(first_line)
            for line in f_in:
                if line.strip():  # 跳过空行
                    parts = line.split()
                    if len(parts) >= 2:
                        var_name = parts[0]
                        value = parts[1]
                        # 检查值是否为0或-0
                        if abs(float(value)) > 1e-6 and var_name[0] != 'z' and var_name[0] != 'e':
                            value = round(float(value))
                            f_out.write(f"{var_name} {value}\n")

        return filtered_file_name