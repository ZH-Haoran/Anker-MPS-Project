class TableName:

    ANKER_WEEK = "安克周"
    FACTORY_CAPACITY = "工厂产能数据"
    FACTORY_PRODUCTION_DAYS = "工厂生产天数"
    CURRENT_INVENTORY = "库存现有量"
    INTRANSIT_PO = "在途PO数据"
    SKU_MAIN = "SKU主数据"
    SOP_PREDICTION = "SOP预测数据"
    WEEK_CAPACITY = "周产能数据"
    REQUIRED_INVENTORY_LEVEL = "要求库存水平"



class AnkerWeek:
    ANKER_WEEK_MONTH_DAY = "安克周-月/日"
    ANKER_WEEK = "安克周"
    ANKER_MONTH = "安克月"

    ## 新增列名 ##
    WEEK = "周"
    MONTH_AND_DAY = "月/日"
    YEAR = "年"
    WEEK_START_DATE = "周起始日期"


class FactoryCapacity:
    BG = "BG"
    PDT = "PDT"
    PN = "PN"
    SUPPLY_CENTER = "供应中心"
    FACTORY = "组装厂"
    PRODUCT_LINE = "产线类别编号"
    UPH = "UPH（PN*产线类别）\n该产线单独生产该PN，对应的UPH"
    HOURS_PER_SHIFT = "hour/班次（产线类别）\n每班次时长"
    SHIFTS_PER_DAY_PER_LINE = "班次/天/每条产线（产线类别）"
    AVAILABLE_LINE_COUNT = "可用产线数（产线类别）"


class WeekCapacity:
    BG = "BG"
    PDT = "PDT"
    PN = "PN"
    SUPPLY_CENTER = "供应中心"
    FACTORY = "组装厂"
    PRODUCT_LINE = "产线类别编号"
    WEEK_CAPACITY = "周产能"

    # SP_PL_PAIR = "组装厂-产线类别编号"


class FactoryProductionDays:
    FACTORY = "组装厂"


class CurrentInventory:
    SUPPLY_CENTER = "供应中心"
    SKU = "SKU"
    QUANTITY = "数量"


class IntransitPO:
    SUPPLIER = "供应商"
    PN = "PN"
    SKU = "SKU编码"
    INTRANSIT_QUANTITY = "未入库数量"
    SUPPLY_CENTER = "供应中心"
    REQUIRED_ARRIVAL_TIME = "要求到货时间"

    ## 新增列名 ##
    REQUIRED_ARRIVAL_WEEK = "要求到货周"
    REQUIRED_ARRIVAL_MODEL_WEEK = "要求到货模型周"
    CAPACITY_OCCUPIED_MODEL_WEEK = "产能占用模型周"


class SKUMain:
    BG = "bg_name"
    PDT = "pdt_name"
    PN = "pn_code"
    SKU = "sku"
    SUPPLY_CENTER = "supply_center"
    SLA_S = "leadtime"
    SAFTY_STOCK_WEEKS = "ss_wks"
    STOCK_OUT_COST = "stock_cost"
    LOSS_SALES_COST = "loss_sales_cost"
    MOQ = "MOQ"

    SLA_T = "运输SLA"


class SOP_PREDICTION:
    SKU = "SKU编码"
    PN = "PN"
    SUPPLY_CENTER = "供应中心"


class RequiredInventoryLevel:
    SKU = "SKU编码"
    PN = "PN"
    SUPPLY_CENTER = "供应中心"