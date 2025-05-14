"""
Lambda function for preprocessing data files.

This module handles the initial preprocessing of data files uploaded to S3:
- Extracts data from Excel files
- Transforms the data into the required format
- Splits data into manageable chunks for batch processing
- Uploads split chunks back to S3
"""

import logging
import math

from src.components.data_management import DataManagement
from src.components.data_transformation import transform_data
from src.lambda_functions.common import check_missing_params
from src.utility import get_cfg


def lambda_handler(event, context):  # pylint: disable=unused-argument
    """
    AWS Lambda handler for preprocessing:
    Transforms data, splits it into chunks, and uploads each chunk to S3.

    Args:
        event (dict): Input event containing bucket, key, run_id, version_id
        context: Context object (unused)

    Returns:
        dict: Response with status code, chunk keys, and metadata
    """
    logging.info("Received event: %s", event)

    required_params = ["bucket", "key", "run_id", "version_id"]

    params = check_missing_params(event, required_params)

    bucket = params["bucket"]
    key = params["key"]
    run_id = params["run_id"]
    version_id = params["version_id"]

    data_management = DataManagement()
    chunk_keys = process_file(data_management, bucket, key, run_id, version_id)

    return {
        "statusCode": 200,
        "body": f"Data transformed and split into {len(chunk_keys)} chunks for run {run_id}.",
        "run_id": run_id,
        "chunk_keys": chunk_keys,
        "version_id": version_id,
    }


def process_file(data_manager, bucket, key, run_id, version_id):
    """
    Process a file by loading, transforming and splitting it into chunks.

    Args:
        data_manager: DataManagement instance
        bucket: S3 bucket name
        key: S3 object key
        run_id: Unique run identifier
        version_id: S3 object version

    Returns:
        list: List of S3 keys for the uploaded chunks
    """
    cfg = get_cfg("lambda/pre_processing.yaml")
    chunk_size = cfg["chunk_size"]

    df, _ = data_manager.load_s3_file(bucket, key, version_id)

    transformed_data = transform_data(df)

    num_chunks = math.ceil(len(transformed_data) / chunk_size)
    chunk_keys = []

    for i in range(num_chunks):
        chunk = transformed_data.iloc[i * chunk_size : (i + 1) * chunk_size]
        chunk_path = f"/tmp/chunk_{i+1:03d}.xlsx"
        chunk.to_excel(chunk_path, index=False)

        chunk_s3_key = f"splits/{run_id}/chunk_{i+1:03d}.xlsx"
        data_manager.upload_excel(
            chunk_path,
            bucket_name=bucket,
            object_name=chunk_s3_key,
            version_id=version_id,
        )
        chunk_keys.append(chunk_s3_key)

    return chunk_keys
