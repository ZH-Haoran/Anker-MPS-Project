# Anker-MPS-Project

我们将整个主生产计划问题划分为两个子模型：主生产计划（MPS）与配送分配（DA），分别确定产品的生产节奏与配送策略。 
 
## 主生产计划模型（MPS） 

主生产计划是将市场需求转化为生产指令的关键决策过程。本研究提出了一个综合考虑多工厂、多产品、多时期的主生产计划优化模型，旨在平衡生产成与库存成本、维护合理的库存水平。    

### 目标函数  最小化总生产成本与延迟惩罚项：  

$$ 
\min \sum_{p \in \mathcal{P}} \left( \sum_{t=1}^T h_p I_{p, t} + \sum_{t=SLA_p^S}^T y_p u_{p, t} + \sum_{t=SLA_p^S}^T w_p s_{p, t} \right) 
$$  

其中，$I_{p, t}$ 为库存水平，$u_{p, t}$ 为未满足的需求数量，$s_{p, t}$ 为未满足的要求库存数量；   
$h_p$, $y_p$ 和 $w_p$ 分别代表对应项的惩罚系数。  

### 模型流程



## 订单分配模型 (DA)
订单分配模型旨在通过将总部和在途订单有限的资源进行合理匹配，以最小化延迟交付成本。

### 目标函数  最小化延迟交付成本

$$
\min \sum_{o\in O_r}(Delay^{RPD}_o \cdot u_o + Delay^{EPD}_o \cdot v_o)
$$

其中，RPD是下游要求交付时间，EPD是总部承诺交付时间，$RPD \geq EPD$, $Delay^{EPD}_o,\;Delay^{RPD}_o$是对应惩罚，$u_o,\; v_o$是对应惩罚系数。
