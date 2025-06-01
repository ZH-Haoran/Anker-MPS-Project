import coptpy as cp
from coptpy import COPT



def delivery_model(T, R, C_r, J, I_p, Q_j, t_j, O_r, d_o, RPD_o, EPD_o, u_o, v_o, p=None):

    delay_list = []
    # Create COPT environment and model
    env = cp.Envr()
    model = env.createModel("Delivery")

    # Create variables
    x = {}  # [order][time]
    y = {}  # [PO][order][time]
    z = {}  # [order][time]
    delay_EPD = {}  # [order]
    delay_RPD = {}  # [order]


    # 通过r索引O[r]找到所有region下的order
    for r in R:
        for o in O_r[r]:
            for t in T:
                x[o, t] = model.addVar(lb=0.0, name=f"x_{o}_{t}")
                z[o, t] = model.addVar(lb=0.0, name=f"z_{o}_{t}")


    for j in J:
        for r in R:
            for o in O_r[r]:
                for t in T:
                    y[j, o, t] = model.addVar(lb=0.0, name=f"y_{j}_{o}_{t}")


    for r in R:
        for o in O_r[r]:
            delay_EPD[o] = model.addVar(lb=0.0, name=f"delay_EPD_{o}")
            delay_RPD[o] = model.addVar(lb=0.0, name=f"delay_RPD_{o}")


    # Objective function: Minimize weighted sum of delays
    obj = cp.LinExpr()
    for r in R:
        for o in O_r[r]:
            obj += delay_RPD[o] * u_o[o] + delay_EPD[o] * v_o[o]


    model.setObjective(obj, sense=COPT.MINIMIZE)



    # Constraints
    # Region capacity constraint
    for r in R:
        for t in T:
            lhs = cp.LinExpr()
            for o in O_r[r]:
                lhs += x[o, t]

                for j in J:
                    if t_j[j] <= t:
                        lhs += y[j, o, t]

            model.addConstr(lhs <= C_r[r], name=f"region_capacity_{r}_{t}")



    # Inventory capacity constraint
    lhs = cp.LinExpr()
    for r in R:
        for o in O_r[r]:
            for t in T:
                lhs += x[o, t]
    model.addConstr(lhs <= next(iter(I_p.values())), name=f"inventory_{p}")



    # PO capacity constraint
    for j in J:
        lhs = cp.LinExpr()
        for r in R:
            for o in O_r[r]:
                for t in T:
                    lhs += y[j, o, t]
        model.addConstr(lhs <= Q_j[j], name=f"PO_{j}")



    # Demand equation
    for t in T:
        for r in R:
            for o in O_r[r]:
                lhs = cp.LinExpr()

                if t >= RPD_o[o]:
                    # Sum of x from RPD to t
                    # for t_prime in range(RPD_o[o], t + 1):
                    for t_prime in T:
                        if t_prime <= t:
                            lhs += x[o, t_prime]

                        # Sum of y from
                        for j in J:
                            if t_j[j] <= t_prime:
                               lhs += y[j, o, t_prime]

                    # Add z variable
                    lhs += z[o, t]
                    model.addConstr(lhs == d_o[o], name=f"demand_{o}_{t}")



    for r in R:
        for o in O_r[r]:
            rhs_epd = cp.LinExpr()
            rhs_rpd = cp.LinExpr()

            for t in T:
                if t >= EPD_o[o]:
                    rhs_epd += z[o, t] * ((t-EPD_o[o]).days + 1)
                if t >= RPD_o[o]:
                    rhs_rpd += z[o, t] * ((t-RPD_o[o]).days + 1)
            # for t in T:
            #     if t >= EPD_o[o]:
            #         rhs_epd += z[o, t] * (t + 1 - EPD_o[o])
            #     if t >= RPD_o[o]:
            #         rhs_rpd += z[o, t] * (t + 1 - RPD_o[o])


            model.addConstr(delay_EPD[o] == rhs_epd, name=f"delay_EPD_{o}")
            model.addConstr(delay_RPD[o] == rhs_rpd, name=f"delay_RPD_{o}")




    # Solve the model
    model.solve()

    # Print solution status
    print(f"Solution status: {model.status}")

    # Extract and print results if optimal
    if model.status == COPT.OPTIMAL:
        print(f"Objective value: {model.objval}")

        # Print variable values
        for j in J:
            for r in R:
                for o in O_r[r]:
                    for t in T:
                        if y[j, o, t].x > 0.0:
                            print(f"{f'y_{j}_{o}_{t}'.ljust(65)} = {y[j, o, t].x:>7.1f}")
                            # print(f"y_{j}_{o}_{t} = {y[j, o, t].x}")

        print()
        for r in R:
            for o in O_r[r]:
                for t in T:
                    if x[o, t].x > 0.0:
                        print(f"{f'x_{o}_{t}'.ljust(45)} = {x[o, t].x:>7.1f}")
                        # print(f"x_{o}_{t} = {x[o, t].x}")

        print()
        for r in R:
            for o in O_r[r]:
                for t in T:
                    if z[o, t].x > 0.0:
                        print(f"z_{o}_{t} = {z[o, t].x}")



    else:
        print("No optimal solution found.")


