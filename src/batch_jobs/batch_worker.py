"""
Batch Worker Module for OpenFOAM simulations.

This module contains functions for processing data chunks in AWS Batch,
running simulations, and storing results back to S3.
"""

import os

from src.components.data_management import DataManagement
from src.components.openfoam_handler import OpenFoamHandler
from src.logger import logging


def batch_worker():
    """
    Main function to handle the batch processing of data.

    This function orchestrates the data management and OpenFOAM simulation tasks.

    Returns:
        None
    """
    bucket = os.environ.get("S3_BUCKET")
    key = os.environ.get("S3_KEY")
    run_id = os.environ.get("RUN_ID")
    version_id = os.environ.get("version_id")

    if not bucket or not key or not run_id or not version_id:
        logging.error(
            "Missing required environment variables: S3_BUCKET, S3_KEY, "
            "RUN_ID, or version_id"
        )
        raise ValueError("Missing required environment variables")

    try:
        job_number = int(key.split("/")[-1].split("_")[1].split(".")[0])
        logging.info(f"Starting Batch Worker for S3 Key: {key}, Run ID: {run_id}")

        data_management = DataManagement()
        df, _ = data_management.load_s3_file(bucket, key)

        print(df)
        openfoam_handler = OpenFoamHandler(df)
        simulation_results = openfoam_handler.simulate()

        output_path = f"/tmp/simulation_result_{run_id}_job_{job_number}.csv"
        simulation_results.to_csv(output_path, index=False)

        result_key = f"simulated/{run_id}/job_{job_number}.csv"
        data_management.upload_csv(output_path, bucket, result_key, version_id)

        logging.info(
            f"Batch Worker completed successfully. Results saved to {result_key}"
        )

    except Exception as e:
        logging.error(f"Error in Batch Worker: {e}")
        raise e


if __name__ == "__main__":
    batch_worker()
