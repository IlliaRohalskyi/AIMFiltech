"""
SageMaker container entrypoint for both training and prediction.
Routes to appropriate script based on SAGEMAKER_PROGRAM environment variable.
"""
import os
from src.logger import logging

def main():
    # Set AWS environment variables
    os.environ["AWS_REGION"] = "eu-central-1"
    os.environ["AWS_DEFAULT_REGION"] = "eu-central-1"
    os.environ["AWS_STS_REGIONAL_ENDPOINTS"] = "regional"
    os.environ["MLFLOW_TRACKING_INSECURE_TLS"] = "true"
    os.environ["MLFLOW_HTTP_REQUEST_TIMEOUT"] = "60"
    os.environ["MLFLOW_HTTP_REQUEST_MAX_RETRIES"] = "5"
    os.environ["MLFLOW_HTTP_REQUEST_BACKOFF_FACTOR"] = "2"
    
    # Get the program to run from environment variable
    program = os.environ.get('SAGEMAKER_PROGRAM', 'train')
    
    logging.info(f"Starting SageMaker container with program: {program}")
    
    try:
        if program == 'train':
            from src.sagemaker.train import run_training
            run_training()
        elif program == 'predict':
            from src.sagemaker.predict import app
            app.run(host="0.0.0.0", port=8080)
        else:
            logging.error(f"Unknown program: {program}. Expected 'train' or 'predict'")
            raise ValueError(f"Unknown program: {program}")
    except Exception as e:
        logging.error(f"Execution failed: {e}")
        raise e


if __name__ == "__main__":
    main()
