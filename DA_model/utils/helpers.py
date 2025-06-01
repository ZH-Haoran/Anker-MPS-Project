"""
Utility functions and helpers for the DA model.
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any, List
import pandas as pd

from config.settings import LOGGING_CONFIG


def setup_logging(log_file: str = None, log_level: str = None) -> None:
    """
    Setup logging configuration.

    Args:
        log_file (str, optional): Log file path
        log_level (str, optional): Logging level
    """
    log_file = log_file or LOGGING_CONFIG['file']
    log_level = log_level or LOGGING_CONFIG['level']
    log_format = LOGGING_CONFIG['format']

    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )


def validate_file_paths(base_directory: str, required_files: List[str]) -> List[str]:
    """
    Validate that all required files exist in the base directory.

    Args:
        base_directory (str): Base directory path
        required_files (List[str]): List of required file names

    Returns:
        List[str]: List of missing files
    """
    missing_files = []

    if not os.path.exists(base_directory):
        raise FileNotFoundError(f"Base directory does not exist: {base_directory}")

    for filename in required_files:
        file_path = os.path.join(base_directory, filename)
        if not os.path.exists(file_path):
            missing_files.append(filename)

    return missing_files


def save_results_to_excel(results: Dict[str, Dict[str, Any]], output_path: str) -> None:
    """
    Save optimization results to Excel file.

    Args:
        results (Dict[str, Dict[str, Any]]): Optimization results
        output_path (str): Output Excel file path
    """
    logger = logging.getLogger(__name__)

    try:
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Summary sheet
            summary_data = []
            for sku, result in results.items():
                summary_data.append({
                    'SKU': sku,
                    'Status': result.get('status', 'Unknown'),
                    'Solution_Found': result.get('solution_found', False),
                    'Objective_Value': result.get('objective_value', 0),
                    'Has_Delays': bool(
                        result.get('delays', {}).get('EPD', {}) or result.get('delays', {}).get('RPD', {}))
                })

            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)

            # Detailed results for each SKU
            for sku, result in results.items():
                if result.get('solution_found', False):
                    # Allocation details
                    allocation_data = []

                    # Inventory allocations
                    for (order, time), quantity in result.get('allocations', {}).get('inventory', {}).items():
                        allocation_data.append({
                            'Type': 'Inventory',
                            'Source': 'Inventory',
                            'Order': str(order),
                            'Time': time,
                            'Quantity': quantity
                        })

                    # PO allocations
                    for (po, order, time), quantity in result.get('allocations', {}).get('purchase_orders', {}).items():
                        allocation_data.append({
                            'Type': 'Purchase_Order',
                            'Source': po,
                            'Order': str(order),
                            'Time': time,
                            'Quantity': quantity
                        })

                    if allocation_data:
                        allocation_df = pd.DataFrame(allocation_data)
                        sheet_name = f"Allocations_{sku}"[:31]  # Excel sheet name limit
                        allocation_df.to_excel(writer, sheet_name=sheet_name, index=False)

        logger.info(f"Results saved to {output_path}")

    except Exception as e:
        logger.error(f"Error saving results to Excel: {e}")
        raise


def calculate_summary_statistics(results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate summary statistics from optimization results.

    Args:
        results (Dict[str, Dict[str, Any]]): Optimization results

    Returns:
        Dict[str, Any]: Summary statistics
    """
    total_skus = len(results)
    successful_optimizations = sum(1 for r in results.values() if r.get('solution_found', False))
    failed_optimizations = total_skus - successful_optimizations

    total_objective_value = sum(
        r.get('objective_value', 0)
        for r in results.values()
        if r.get('solution_found', False)
    )

    # Count orders with delays
    orders_with_epd_delays = 0
    orders_with_rpd_delays = 0
    total_delayed_orders = set()

    for result in results.values():
        if result.get('solution_found', False):
            delays = result.get('delays', {})
            epd_delayed = set(delays.get('EPD', {}).keys())
            rpd_delayed = set(delays.get('RPD', {}).keys())

            orders_with_epd_delays += len(epd_delayed)
            orders_with_rpd_delays += len(rpd_delayed)
            total_delayed_orders.update(epd_delayed)
            total_delayed_orders.update(rpd_delayed)

    return {
        'total_skus': total_skus,
        'successful_optimizations': successful_optimizations,
        'failed_optimizations': failed_optimizations,
        'success_rate': successful_optimizations / total_skus if total_skus > 0 else 0,
        'total_objective_value': total_objective_value,
        'orders_with_epd_delays': orders_with_epd_delays,
        'orders_with_rpd_delays': orders_with_rpd_delays,
        'unique_delayed_orders': len(total_delayed_orders)
    }


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds (float): Duration in seconds

    Returns:
        str: Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.2f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"


def create_optimization_report(results: Dict[str, Dict[str, Any]],
                               execution_time: float = None) -> str:
    """
    Create a formatted optimization report.

    Args:
        results (Dict[str, Dict[str, Any]]): Optimization results
        execution_time (float, optional): Total execution time in seconds

    Returns:
        str: Formatted report
    """
    stats = calculate_summary_statistics(results)

    report = f"""
=== DELIVERY OPTIMIZATION REPORT ===
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY STATISTICS:
- Total SKUs processed: {stats['total_skus']}
- Successful optimizations: {stats['successful_optimizations']}
- Failed optimizations: {stats['failed_optimizations']}
- Success rate: {stats['success_rate']:.1%}

PERFORMANCE METRICS:
- Total weighted delay cost: {stats['total_objective_value']:.2f}
- Orders with EPD delays: {stats['orders_with_epd_delays']}
- Orders with RPD delays: {stats['orders_with_rpd_delays']}
- Unique delayed orders: {stats['unique_delayed_orders']}
"""

    if execution_time is not None:
        report += f"- Total execution time: {format_duration(execution_time)}\n"

    report += "\nDETAILED RESULTS BY SKU:\n"
    report += "-" * 50 + "\n"

    for sku, result in results.items():
        status = "✓ Optimal" if result.get('solution_found', False) else "✗ Failed"
        obj_val = result.get('objective_value', 0)

        report += f"SKU: {sku}\n"
        report += f"  Status: {status}\n"

        if result.get('solution_found', False):
            report += f"  Objective Value: {obj_val:.2f}\n"

            delays = result.get('delays', {})
            epd_delays = len(delays.get('EPD', {}))
            rpd_delays = len(delays.get('RPD', {}))

            if epd_delays > 0 or rpd_delays > 0:
                report += f"  Delayed Orders: {epd_delays} EPD, {rpd_delays} RPD\n"
        else:
            error = result.get('error', 'Unknown error')
            report += f"  Error: {error}\n"

        report += "\n"

    report += "=" * 40

    return report