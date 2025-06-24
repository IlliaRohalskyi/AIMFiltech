"""
Lambda function for post-processing simulation results.

This module handles the aggregation of simulation results:
- Lists all simulation result files from the run
- Combines them into a single consolidated file
- Uploads the combined result to S3
"""

import logging
import os
from typing import Any, Dict, List

import boto3
import pandas as pd

from src.components.data_management import DataManagement
from src.lambda_functions.common import check_missing_params


def lambda_handler(event, context) -> Dict[str, Any]:  # pylint: disable=unused-argument
    """
    AWS Lambda handler for post-processing simulation results.

    Args:
        event (dict): Input containing run_id, bucket, version_id
        context: Lambda context object (unused)

    Returns:
        dict: Response with status code and output file information
    """
    logging.info("Received event: %s", event)

    required_params = ["bucket", "run_id", "version_id"]
    params = check_missing_params(event, required_params)
    bucket = params["bucket"]
    run_id = params["run_id"]
    version_id = params["version_id"]

    try:
        result_keys = list_simulation_results(bucket, run_id)
        logging.info("Found %d result files: %s", len(result_keys), result_keys)

        if not result_keys:
            logging.error("No simulation results found for run %s", run_id)
            return {
                "statusCode": 404,
                "error": f"No simulation results found for run {run_id}",
                "run_id": run_id,
            }

        data_management = DataManagement()
        combined_df = combine_excel_files(data_management, bucket, result_keys)

        local_output_path = f"/tmp/combined_results_{run_id}.xlsx"
        combined_df.to_excel(local_output_path, index=False)

        s3_prefix = f"combined/{run_id}/"
        output_key = os.path.join(s3_prefix, "combined_results.xlsx")
        data_management.upload_excel(local_output_path, bucket, output_key, version_id)
        logging.info("Uploaded combined results to %s", output_key)

        return {
            "statusCode": 200,
            "body": f"Successfully combined {len(result_keys)} simulation results for run {run_id}",
            "output_key": output_key,
            "run_id": run_id,
            "files_combined": result_keys,
            "output_path": f"s3://{bucket}/{s3_prefix}",
        }

    except Exception as e:  # pylint: disable=broad-except
        logging.error("Error in post-processing: %s", str(e), exc_info=True)
        return {
            "statusCode": 500,
            "error": f"Post-processing failed: {str(e)}",
            "run_id": run_id,
        }


def list_simulation_results(bucket: str, run_id: str) -> List[str]:
    """
    List all simulation result files for a specific run.

    Args:
        bucket: S3 bucket name
        run_id: Run identifier

    Returns:
        List of S3 keys for simulation result files
    """
    s3_client = boto3.client("s3")
    prefix = f"simulated/{run_id}/"
    logging.info("Listing objects with prefix %s", prefix)

    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)

        if "Contents" not in response:
            logging.warning("No objects found with prefix %s", prefix)
            return []

        result_keys = [
            obj["Key"] for obj in response["Contents"] if obj["Key"].endswith(".xlsx")
        ]

        logging.info("Found %d Excel files", len(result_keys))
        return result_keys

    except Exception as e:
        logging.error("Error listing S3 objects: %s", str(e), exc_info=True)
        raise


def combine_excel_files(
    data_management: DataManagement, bucket: str, file_keys: List[str]
) -> pd.DataFrame:
    """
    Load multiple Excel files and combine them into a single DataFrame.

    Args:
        data_management: DataManagement instance
        bucket: S3 bucket name
        file_keys: List of S3 object keys
        version_id: Version ID for consistency

    Returns:
        Combined DataFrame of all simulationW results
    """
    dataframes = []
    success_count = 0

    for key in file_keys:
        try:
            logging.info("Loading file: %s", key)
            df, _ = data_management.load_s3_file(bucket, key)
            logging.info("Successfully loaded %s, shape: %s", key, df.shape)
            dataframes.append(df)
            success_count += 1
        except Exception as e:  # pylint: disable=broad-except
            logging.error("Failed to load file %s: %s", key, str(e), exc_info=True)

    if not dataframes:
        raise ValueError(f"Could not load any of the {len(file_keys)} data files")

    logging.info("Successfully loaded %d of %d files", success_count, len(file_keys))

    combined_df = pd.concat(dataframes, ignore_index=True)
    logging.info("Combined DataFrame shape: %s", combined_df.shape)
    return combined_df
