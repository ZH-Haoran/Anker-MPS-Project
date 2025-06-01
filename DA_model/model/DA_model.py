"""
Delivery optimization model using linear programming.
"""

import coptpy as cp
from coptpy import COPT
from typing import Dict, List, Any, Optional, Tuple
import logging

from config.settings import OPTIMIZATION_CONFIG

logger = logging.getLogger(__name__)


class DeliveryOptimizer:
    """Handles the linear programming optimization for delivery scheduling."""

    def __init__(self, solver_timeout: int = None):
        """
        Initialize the DeliveryOptimizer.

        Args:
            solver_timeout (int, optional): Solver timeout in seconds
        """
        self.solver_timeout = solver_timeout or OPTIMIZATION_CONFIG['solver_timeout']
        self.env = cp.Envr()

    def create_model(self, params: Dict[str, Any]) -> Tuple[cp.Model, Dict]:
        """
        Create the optimization model with variables and constraints.

        Args:
            params (Dict[str, Any]): Optimization parameters

        Returns:
            Tuple[cp.Model, Dict]: The model and decision variables
        """
        model = self.env.createModel("DeliveryOptimization")

        # Extract parameters
        T = params['T']
        R = params['R']
        C_r = params['C_r']
        J = params['J']
        I_p = params['I_p']
        Q_j = params['Q_j']
        t_j = params['t_j']
        O_r = params['O_r']
        d_o = params['d_o']
        RPD_o = params['RPD_o']
        EPD_o = params['EPD_o']
        u_o = params['u_o']
        v_o = params['v_o']
        sku = params['sku']

        # Decision variables
        variables = {}

        # x[order, time]: inventory allocation to order at time
        x = {}
        for r in R:
            for o in O_r[r]:
                for t in T:
                    x[o, t] = model.addVar(lb=0.0, name=f"x_{o}_{t}")
        variables['x'] = x

        # y[po, order, time]: PO allocation to order at time
        y = {}
        for j in J:
            for r in R:
                for o in O_r[r]:
                    for t in T:
                        y[j, o, t] = model.addVar(lb=0.0, name=f"y_{j}_{o}_{t}")
        variables['y'] = y

        # z[order, time]: unmet demand for order at time
        z = {}
        for r in R:
            for o in O_r[r]:
                for t in T:
                    z[o, t] = model.addVar(lb=0.0, name=f"z_{o}_{t}")
        variables['z'] = z

        # delay variables
        delay_EPD = {}
        delay_RPD = {}
        for r in R:
            for o in O_r[r]:
                delay_EPD[o] = model.addVar(lb=0.0, name=f"delay_EPD_{o}")
                delay_RPD[o] = model.addVar(lb=0.0, name=f"delay_RPD_{o}")
        variables['delay_EPD'] = delay_EPD
        variables['delay_RPD'] = delay_RPD

        # Objective function: Minimize weighted delays
        obj = cp.LinExpr()
        for r in R:
            for o in O_r[r]:
                obj += delay_RPD[o] * u_o[o] + delay_EPD[o] * v_o[o]
        model.setObjective(obj, sense=COPT.MINIMIZE)

        # Add constraints
        self._add_constraints(model, variables, params)

        return model, variables

    def _add_constraints(self, model: cp.Model, variables: Dict, params: Dict[str, Any]) -> None:
        """
        Add all constraints to the optimization model.

        Args:
            model (cp.Model): The optimization model
            variables (Dict): Decision variables
            params (Dict[str, Any]): Optimization parameters
        """
        T = params['T']
        R = params['R']
        C_r = params['C_r']
        J = params['J']
        I_p = params['I_p']
        Q_j = params['Q_j']
        t_j = params['t_j']
        O_r = params['O_r']
        d_o = params['d_o']
        RPD_o = params['RPD_o']
        EPD_o = params['EPD_o']
        sku = params['sku']

        x = variables['x']
        y = variables['y']
        z = variables['z']
        delay_EPD = variables['delay_EPD']
        delay_RPD = variables['delay_RPD']

        # Region capacity constraints
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
        model.addConstr(lhs <= next(iter(I_p.values())), name=f"inventory_{sku}")

        # PO capacity constraints
        for j in J:
            lhs = cp.LinExpr()
            for r in R:
                for o in O_r[r]:
                    for t in T:
                        lhs += y[j, o, t]
            model.addConstr(lhs <= Q_j[j], name=f"PO_{j}")

        # Demand satisfaction constraints
        for t in T:
            for r in R:
                for o in O_r[r]:
                    if t >= RPD_o[o]:
                        lhs = cp.LinExpr()

                        # Sum allocations up to time t
                        for t_prime in T:
                            if t_prime <= t:
                                lhs += x[o, t_prime]
                                for j in J:
                                    if t_j[j] <= t_prime:
                                        lhs += y[j, o, t_prime]

                        # Add unmet demand
                        lhs += z[o, t]
                        model.addConstr(lhs == d_o[o], name=f"demand_{o}_{t}")

        # Delay calculation constraints
        for r in R:
            for o in O_r[r]:
                rhs_epd = cp.LinExpr()
                rhs_rpd = cp.LinExpr()

                for t in T:
                    if t >= EPD_o[o]:
                        rhs_epd += z[o, t] * ((t - EPD_o[o]).days + 1)
                    if t >= RPD_o[o]:
                        rhs_rpd += z[o, t] * ((t - RPD_o[o]).days + 1)

                model.addConstr(delay_EPD[o] == rhs_epd, name=f"delay_EPD_{o}")
                model.addConstr(delay_RPD[o] == rhs_rpd, name=f"delay_RPD_{o}")

    def solve_model(self, model: cp.Model, variables: Dict, sku: str) -> Dict[str, Any]:
        """
        Solve the optimization model and return results.

        Args:
            model (cp.Model): The optimization model
            variables (Dict): Decision variables
            sku (str): SKU being optimized

        Returns:
            Dict[str, Any]: Optimization results
        """
        logger.info(f"Solving optimization model for SKU: {sku}")

        # Set solver parameters
        model.setParam(COPT.Param.TimeLimit, self.solver_timeout)

        # Solve the model
        try:
            model.solve()
        except Exception as e:
            logger.error(f"Error solving model for SKU {sku}: {e}")
            return {'status': 'error', 'error': str(e)}

        # Extract results
        results = {
            'sku': sku,
            'status': model.status,
            'solution_found': model.status == COPT.OPTIMAL,
            'objective_value': None,
            'allocations': {},
            'delays': {},
            'unmet_demands': {}
        }

        if model.status == COPT.OPTIMAL:
            results['objective_value'] = model.objval

            # Extract variable values
            x = variables['x']
            y = variables['y']
            z = variables['z']
            delay_EPD = variables['delay_EPD']
            delay_RPD = variables['delay_RPD']

            # Store allocation results
            allocations = {'inventory': {}, 'purchase_orders': {}}
            for key, var in x.items():
                if var.x > 1e-6:  # Only store non-zero values
                    allocations['inventory'][key] = var.x

            for key, var in y.items():
                if var.x > 1e-6:
                    allocations['purchase_orders'][key] = var.x

            results['allocations'] = allocations

            # Store delay information
            delays = {'EPD': {}, 'RPD': {}}
            for order, var in delay_EPD.items():
                if var.x > 1e-6:
                    delays['EPD'][order] = var.x

            for order, var in delay_RPD.items():
                if var.x > 1e-6:
                    delays['RPD'][order] = var.x

            results['delays'] = delays

            # Store unmet demands
            unmet_demands = {}
            for key, var in z.items():
                if var.x > 1e-6:
                    unmet_demands[key] = var.x

            results['unmet_demands'] = unmet_demands

            logger.info(f"Optimization completed for SKU {sku}: objective = {model.objval:.2f}")

        else:
            logger.warning(f"No optimal solution found for SKU {sku}: status = {model.status}")

        return results

    def optimize_single_sku(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize delivery for a single SKU.

        Args:
            params (Dict[str, Any]): Optimization parameters for the SKU

        Returns:
            Dict[str, Any]: Optimization results
        """
        sku = params['sku']

        try:
            # Create and solve model
            model, variables = self.create_model(params)
            results = self.solve_model(model, variables, sku)

            # Clean up
            # model.dispose()

            return results

        except Exception as e:
            logger.error(f"Error optimizing SKU {sku}: {e}")
            return {
                'sku': sku,
                'status': 'error',
                'error': str(e),
                'solution_found': False
            }

    def optimize_all_skus(self, all_params: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Optimize delivery for all SKUs.

        Args:
            all_params (List[Dict[str, Any]]): List of optimization parameters for each SKU

        Returns:
            Dict[str, Dict[str, Any]]: Results for each SKU
        """
        logger.info(f"Starting optimization for {len(all_params)} SKUs")

        results = {}
        successful_optimizations = 0

        for i, params in enumerate(all_params, 1):
            sku = params['sku']
            logger.info(f"Optimizing SKU {i}/{len(all_params)}: {sku}")

            result = self.optimize_single_sku(params)
            results[sku] = result

            if result['solution_found']:
                successful_optimizations += 1

        logger.info(f"Optimization completed: {successful_optimizations}/{len(all_params)} SKUs successfully optimized")

        return results

    def print_results_summary(self, results: Dict[str, Dict[str, Any]]) -> None:
        """
        Print a summary of optimization results.

        Args:
            results (Dict[str, Dict[str, Any]]): Results from optimization
        """
        total_skus = len(results)
        successful = sum(1 for r in results.values() if r['solution_found'])
        total_objective = sum(r.get('objective_value', 0) for r in results.values() if r['solution_found'])

        print(f"\n=== Optimization Results Summary ===")
        print(f"Total SKUs processed: {total_skus}")
        print(f"Successfully optimized: {successful}")
        print(f"Failed optimizations: {total_skus - successful}")
        print(f"Total weighted delay cost: {total_objective:.2f}")

        # Count delayed orders
        delayed_orders = 0
        for result in results.values():
            if result['solution_found']:
                delays = result.get('delays', {})
                delayed_orders += len(set(list(delays.get('EPD', {}).keys()) + list(delays.get('RPD', {}).keys())))

        print(f"Total orders with delays: {delayed_orders}")
        print("="*40)