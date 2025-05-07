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
    job_number = os.environ.get("BATCH_JOB_INDEX")
    version_id = os.environ.get("version_id")

    if not bucket or not key or not run_id or not job_number or not version_id:
        logging.error("Missing required environment variables: S3_BUCKET, S3_KEY, RUN_ID, BATCH_JOB_INDEX or version_id")
        Exception("Missing required environment variables")

    try:
        logging.info(f"Starting Batch Worker for S3 Key: {key}, Run ID: {run_id}")
        
        data_management = DataManagement()
        df, _ = data_management.load_s3_file(bucket, key)

        openfoam_handler = OpenFoamHandler(df)
        simulation_results = openfoam_handler.simulate()

        output_path = f"/tmp/simulation_result_{run_id}_job_{job_number}.xlsx"
        simulation_results.to_excel(output_path, index=False)

        result_key = f"simulated/{run_id}/job_{job_number}.xlsx"
        data_management.upload_excel(output_path, bucket, result_key, version_id)

        logging.info(f"Batch Worker completed successfully. Results saved to {result_key}")

    except Exception as e:
        logging.error(f"Error in Batch Worker: {e}")

if __name__ == "__main__":
    batch_worker()