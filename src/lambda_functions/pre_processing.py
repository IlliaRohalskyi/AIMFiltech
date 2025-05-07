import os
import math
import uuid
from src.components.data_management import DataManagement
from src.components.data_transformation import transform_data
from src.utility import get_cfg


def lambda_handler(event, context):
    """
    AWS Lambda handler for preprocessing: 
    Transforms data, splits it into chunks, and uploads each chunk to S3.
    """
    cfg = get_cfg("lambda/pre_processing.yaml")
    chunk_size = cfg["chunk_size"]

    run_id = str(uuid.uuid4())

    data_management = DataManagement()
    df, version_id = data_management.initiate_data_ingestion()

    transformed_data = transform_data(df)

    num_chunks = math.ceil(len(transformed_data) / chunk_size)
    chunk_keys = []
    for i in range(num_chunks):
        chunk = transformed_data.iloc[i*chunk_size : (i+1)*chunk_size]
        chunk_path = f"/tmp/chunk_{i+1:03d}.csv"
        chunk.to_csv(chunk_path, index=False)

        chunk_s3_key = f"splits/{run_id}/chunk_{i+1:03d}.csv"
        data_management.upload_excel(
            chunk_path,
            bucket_name=os.environ["S3_BUCKET"],
            object_name=chunk_s3_key,
            version_id=version_id
        )
        chunk_keys.append(chunk_s3_key)

    return {
        "statusCode": 200,
        "body": f"Data transformed and split into {num_chunks} chunks for run {run_id}.",
        "run_id": run_id,
        "chunk_keys": chunk_keys,
        "version_id": version_id,
    }