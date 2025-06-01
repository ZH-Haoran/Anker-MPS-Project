from DA_model._raw_code.Delivery_model_SKU import delivery_model
from DA_model._raw_code.Data_Cleaning import clean_data
from DA_model._raw_code.Data_split_SKU import split_by_sku


if __name__ == '__main__':
    # Load data
    base_path = './订单分配模型脱敏数据'
    inventory, order, po, region_capacity = clean_data(base_path)

    unique_sku = set(order['sku'])


    delay_ = []

    for sku in unique_sku:
        # Split data by sku
        params = split_by_sku(inventory, order, po, region_capacity, sku)
        # Run delivery model
        delay_list = delivery_model(*params)
        if delay_list != []:
            delay_.append({sku:delay_list})


    print('Total SKUs: ', len(unique_sku))
    print(delay_)
    print('Number of SKUs that delay: ', len(delay_))

    count = 0
    for i in delay_:
        for j in i:
            for k in j:
                count += 1

    print('Total number of Order that delay: ', count)
