# Anker-MPS-Project

我们将整个主生产计划问题划分为两个子模型：主生产计划（MPS）与配送分配（DA），分别确定产品的生产节奏与配送策略。 
 
## 主生产计划模型（MPS） 

主生产计划是将市场需求转化为生产指令的关键决策过程。本研究提出了一个综合考虑多工厂、多产品、多时期的主生产计划优化模型，旨在平衡生产成与库存成本、维护合理的库存水平。    

## 订单分配模型 (DA)
订单分配模型旨在通过将总部和在途订单有限的资源进行合理匹配，以最小化延迟交付成本。


## Setup
### 安装 Python 依赖  
```
git clone https://github.com/ZH-Haoran/Anker-MPS-Project.git  
pip install -r requirements.txt
```

## 运行 MPS 模型：  

### 数据准备：  
MPS 模型需要以下七个 excel 文件作为模型输入：
1. 安克周.xlsx
2. 工厂产能数据.xlsx
3. 工厂生产天数.xlsx
4. 库存现有量.xlsx
5. 在途PO数据.xlsx
6. SKU主数据.xlsx
7. SOP预测数据.xlsx  

表格结构参考脱敏数据样例。数据应当被放入 `/MPS_model/data/raw/` 文件夹下。

### 模型求解
代码目前使用 COPT 求解器进行求解，需要提前配置 COPT 的 license，具体可以参照 [COPT 官网](https://www.shanshu.ai/copt)。
配置完毕后，进入到 MPS_model 文件夹下，运行 `main.py` 文件即可。  
main.py 中有一些自定义的运行参数：  
1. start_week: 指计划的起始周，总计划范围从起始周开始共持续 26 周。如起始周为 “2025W1”，那么计划范围为 “2025W1” - “2026W26”。
2. solver_params：这是求解器的求解参数，具体可参照 [COPT 求解器参数](https://guide.coap.online/copt/zh-doc/parameter.html)。
3. relax_decision_vars：是否将下单量的决策变量从整数松弛为连续形式，对应报告中 `Sec. 2.2.3. 求解加速` 段。
4. visualize：是否在求解结束后可视化库存变化曲线。  

由于代码会输出记录了所有模型信息的 `.mps` 文件，因此也可以使用该文件在 [COAP](https://www.coap.online) (Center of Optimization Algorithm Patform) 求解问题，求解效率会有所提升。

### MPS 模型代码结构
* `/MPS_model/data/` 
  * `raw/` : 存放原始数据文件
  * `modified/` : 存放经过 DataModifier 编辑的表格，在模型数据预处理阶段被创建
  * `data_reader.py` : 读取原始数据表格并进行初步清洗
* `/MPS_model/data_processor/`
  * `data_modifier.py` : 对原始数据表格进行编辑，从原始数据中计算模型所需的参数
  * `model_params_generator.py` : 从经过编辑的表格中获取模型参数，并以合适的数据结构保存为类属性
  * `data_preprocessor.py` : 向模型传递模型参数类
* `/MPS_model/models/`
  * `MPS_model.py` : 封装求解 MPS 模型的主要流程，包括添加变量、添加约束和求解模型等
* `/MPS_model/util/`
  * `data_loader.py` : 数据预处理和传递模型参数的实际执行函数
  * `data_visualizer.py` : 读取求解输出的`.sol` 文件记录模型求解结果，可视化本次模型运筹各 SKU 的库存曲线，图片输出至 `MPS_model/visualization/` 文件夹下
  * `header.py` : 各表格表头，后续如调整列名可在此修改
  * `model_writer.py` : 输出求解结果的 `.sol` 文件至 `/MPS_model/output/` 文件夹下，并执行后处理，四舍五入求解结果（以整数类型求解和非整数类型求解都会执行，因为整数类型求解由于相对容差或数值精度也会有小数解情况，只是小数会十分接近整数）
* `/MPS_model/mps/` : 存放每次模型运行的 `.mps` 文件，该文件会记录所有变量和约束信息
* `/MPS_model/output/` : 存放每次模型运行的 `.sol` 文件，该文件会记录模型的求解结果
* `/MPS_model/visualization/` : 存放模型库存曲线的可视化结果
* `/MPS_model/main.py` : 模型主函数

### MPS 模型备注
1. 目前与产品下市有关的数据预处理逻辑和模型约束实现（对应报告中 `Sec. 2.2.1 停产约束` 段）由于数据缺失还未被整合入代码中。
2. 运输 SLA 数据目前缺失，在 data_processor.data_modifier 的 DataModifier 类中我们暂时填补了一列 1 作为运输 SLA，后续可能需按需修改。
3. 目前未完善将求解结果写入 excel 或数据库中的流程，但大致流程可以参考 DataVisualizer 类的 `_parse_sol_file()` 函数。后续具体以什么格式输出待确定。
4. 我们将当前环境下的所有包都导出到了 `requiments.txt` 中，如果配置环境出现问题，可以只安装 `numpy` , `pandas` , `matplotlib` 和 `coptpy` ，其他包应当均为这些必要包的依赖。




## 运行 DA 模型：

### 数据准备：  
DA 模型需要以下四个 excel 文件作为模型输入：
1. 库存可用量快照导出.xlsx
2. 履行订单快照导出.xlsx
3. 在途PO工单快照导出.xlsx
4. 区域订单上限快照.xlsx

表格结构参考脱敏数据样例。数据应当被放入 /DA_model/raw_data/ 文件夹下。\
备注：由于数据缺失，我们手工生成了`区域订单上线快照.xlsx`， 每个SKU的区域上限都被设置为100000。


### 模型求解
代码目前使用 COPT 求解器进行求解，需要提前配置 COPT 的 license，具体可以参照 COPT 官网。
配置完毕后，进入到 DA_model/ 文件夹下，在终端运行 main.py 文件即可。\

#### 具体命令如下（以macOS Terminal为例）：
```
cd Anker-MPS-Project/DA_model
python3 main.py --data raw_data --output results --log-level INFO
```
其中 raw_data 为数据文件夹路径，results 为输出文件夹路径，log-level 为日志级别，可选 DEBUG、INFO、WARNING、ERROR。


### DA 模型代码结构
```
DA_model/
├── setup.py
├── main.py
├── config/
│   ├── .gitkeep
│   └── settings.py
├── data_processor/
│   ├── .gitkeep
│   ├── loader.py
│   ├── cleaner.py
│   └── processor.py
├── raw_data/
│   ├── 区域订单上限快照.xlsx
│   ├── 库存可用量快照导出.xlsx
│   ├── 履行订单快照导出.xlsx
│   └── 在途PO工单快照导出.xlsx
├── results/
│   ├── .gitkeep
│   ├── optimization.log
│   ├── optimization_results.txt
│   └── optimization_results.xlsx
├── models/
│   ├── .gitkeep
│   └── DA_model.py
├── utils/
│   ├── .gitkeep
├── └── helpers.py
└── _raw_code/
```

* `/DA_model/raw_data/` 
  * 存放原始数据文件:
  * `区域订单上限快照.xlsx` 
  * `库存可用量快照导出.xlsx` 
  * `履行订单快照导出.xlsx` 
  * `在途PO工单快照导出.xlsx` 
* `/DA_model/config/` 
  * `settings.py` : 配置文件，包括所需数据表名、列名、参数名等
* `/DA_model/data_processor/`
  * `loader.py` : 从原始数据表格中加载所需要的数据，传递给模型
  * `cleaner.py` : 对传递数据进行数据清洗，从中计算模型所需的参数
  * `processor.py` : 将清洗后参数根据SKU进行分类打包（降低模型维度）
* `/DA_model/models/`
  * `DA_model.py` : 封装求解DA模型的主要流程，包括添加变量、添加约束和求解模型等
* `/DA_model/util/`
  * `helpers.py` : 辅助函数，如日志记录、生成优化报告、结果核实、结果excel储存等
* `/DA_model/results/` : 存放模型运行的日志文件和结果文件
* `/DA_model/main.py` : 模型主函数
* `/DA_model/_raw_code/` : 原始未经处理的代码版本


### DA 模型备注
