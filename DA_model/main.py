"""
Main script for running the delivery optimization system.
"""

import argparse
import os
import time
from typing import Optional

from data_processor.loader import DataLoader
from data_processor.cleaner import DataCleaner
from data_processor.processor import DataProcessor
from model.DA_model import DeliveryOptimizer
from utils.helpers import (
    setup_logging,
    save_results_to_excel,
    create_optimization_report,
    validate_file_paths
)
from config.settings import FILE_NAMES


def main(data_directory: str, output_directory: str = None, log_level: str = "INFO") -> None:
    """
    Main function to run the delivery optimization process.

    Args:
        data_directory (str): Path to directory containing input Excel files
        output_directory (str, optional): Path to directory for output files
        log_level (str): Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Setup logging
    if output_directory:
        os.makedirs(output_directory, exist_ok=True)
        log_file = os.path.join(output_directory, "optimization.log")
    else:
        log_file = "optimization.log"

    setup_logging(log_file=log_file, log_level=log_level)

    import logging
    logger = logging.getLogger(__name__)

    logger.info("=== Starting Delivery Optimization Process ===")
    start_time = time.time()

    try:
        # Validate input files
        required_files = list(FILE_NAMES.values())
        missing_files = validate_file_paths(data_directory, required_files)
        if missing_files:
            raise FileNotFoundError(f"Missing required files: {missing_files}")

        # Step 1: Load data
        logger.info("Step 1: Loading data...")
        loader = DataLoader(data_directory)
        inventory_df, orders_df, po_df, region_capacity_df = loader.load_all()

        # Step 2: Clean data
        logger.info("Step 2: Cleaning data...")
        cleaner = DataCleaner()
        cleaned_inventory, cleaned_orders, cleaned_po, cleaned_region_capacity = cleaner.clean_all(
            inventory_df, orders_df, po_df, region_capacity_df
        )

        # Step 3: Process data by SKU
        logger.info("Step 3: Processing data by SKU...")
        processor = DataProcessor()
        unique_skus = processor.get_unique_skus(cleaned_orders)
        logger.info(f"Found {len(unique_skus)} unique SKUs")

        # Prepare optimization parameters for each SKU
        all_params = []
        for sku in unique_skus:
            params = processor.process_sku(
                cleaned_inventory, cleaned_orders, cleaned_po, cleaned_region_capacity, sku
            )
            if params is not None:
                all_params.append(params)

        logger.info(f"Prepared optimization parameters for {len(all_params)} SKUs")

        # Step 4: Run optimization
        logger.info("Step 4: Running optimization...")
        optimizer = DeliveryOptimizer()
        results = optimizer.optimize_all_skus(all_params)

        # Step 5: Generate outputs
        execution_time = time.time() - start_time
        logger.info(f"Optimization completed in {execution_time:.2f} seconds")

        # Print summary to console
        optimizer.print_results_summary(results)

        # Generate detailed report
        report = create_optimization_report(results, execution_time)
        print(report)

        # Save results to files if output directory specified
        if output_directory:
            # Save Excel results
            excel_path = os.path.join(output_directory, "optimization_results.xlsx")
            save_results_to_excel(results, excel_path)

            # Save text report
            report_path = os.path.join(output_directory, "optimization_report.txt")
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)

            logger.info(f"Results saved to {output_directory}")

        logger.info("=== Delivery Optimization Process Completed Successfully ===")

    except Exception as e:
        logger.error(f"Error during optimization process: {e}")
        raise


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Delivery Optimization System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --data ./data
  python main.py --data ./data --output ./results
  python main.py --data ./data --output ./results --log-level DEBUG
        """
    )

    parser.add_argument(
        '--data', '-d',
        required=True,
        help='Path to directory containing input Excel files'
    )

    parser.add_argument(
        '--output', '-o',
        default=None,
        help='Path to directory for output files (optional)'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    main(
        data_directory=args.data,
        output_directory=args.output,
        log_level=args.log_level
    )