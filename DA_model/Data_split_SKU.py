import numpy as np
import pandas as pd


def split_by_sku(inventory, order, po, region_capacity, p=None):
    """
    Parameters:
        - inventory (dataframe)
        - order (dataframe)
        - po (dataframe)
        - region_capacity (dataframe)
        - p (string): The SKU to split the data by.

    Returns:  lists input and dictionaries input for model 2.
        - time_set (list):
        - region_set (list):
        - J (list): PO's code
        - I_p (dictionary): SKU p's inventory
        - Q_j (dictionary): PO j's quantity
        - t_j (dictionary): PO j's arrival time
        - O_r (dictionary): order o under region r
        - d_o (dictionary): order o's demand
        - RPD_o (dictionary): order o's RDP
        - EPD_o (dictionary): order o's EPD
        - u_o (dictionary): order o's RPD penalty
        - v_o (dictionary): order o's EPD penalty
    """


    if p is None:
        print("Please provide a SKU to split the data by.")
    else:

        po_p = po[po['sku'] == p]
        order_p = order[order['sku'] == p]
        inventory_p = inventory[inventory['sku'] == p]
        region_capacity_p = region_capacity[region_capacity['sku'] == p]
        # print(po_p.head())
        # print(order_p.head())
        # print(inventory_p.head())
        # print(region_capacity_p.head())

        # unique time set
        times = pd.concat([po_p['arrival time'], order_p['RPD'], order_p['EPD']])
        unique_time = np.sort(times.unique())
        time_set = list(unique_time)

        # Region set
        region_set = list(order['region'].unique())

        # C_r (capacity upperbound of region r at time t)
        C_r = dict()
        for r in region_set:
            C_r[r] = region_capacity_p[region_capacity_p['region'] == r]['capacity'].values[0]


        # I_p (inventory quantity)
        I_p = dict()
        if inventory_p.empty:
            I_p[p] = 0
        else:
            I_p[p] = inventory_p[inventory_p['sku'] == p]['inventory'].values[0]

        # J (PO's code)
        J = list(po_p['batch code'].unique())

        # Q_j (PO j's quantity)
        Q_j = dict()
        for code in J:
            Q_j[code] = po_p[po_p['batch code'] == code]['quantity'].values[0]

        # O_r (order's under region r)
        O_r = dict()
        for r in region_set:
            O_r[r] = order_p[order_p['region'] == r]['unique code'].to_list()


        # P_j (PO and corresponding product)
        P_j = dict()
        for code in po_p['batch code']:
            P_j[code] = po_p[po_p['batch code'] == code]['sku'].values

        # t_j (PO's arrival time)
        t_j = dict()
        for code in po_p['batch code']:
            t_j[code] = po_p[po_p['batch code'] == code]['arrival time'].values[0]


        # d_o (order o's demand)
        d_o = dict()
        for region in region_set:
            for code in O_r[region]:
                d_o[code] = order_p[order_p['unique code'] == code]['quantity'].values[0]

        # RPD_o (order o's RPD)
        RPD_o = dict()
        for region in region_set:
            for code in O_r[region]:
                RPD_o[code] = order_p[order_p['unique code'] == code]['RPD'].values[0]

        # EPD_o (order o's EPD)
        EPD_o = dict()
        for region in region_set:
            for code in O_r[region]:
                EPD_o[code] = order_p[order_p['unique code'] == code]['EPD'].values[0]

        # delay penalty
        u_o = dict()  # RPD penalty
        v_o = dict()  # EPD penalty
        for region in region_set:
            for code in O_r[region]:
                u_o[code] = 1
                v_o[code] = 10

        return (time_set, region_set, C_r, J, I_p, Q_j, t_j, O_r, d_o, RPD_o, EPD_o, u_o, v_o)