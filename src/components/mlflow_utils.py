import os
import json
import boto3
import mlflow
import mlflow.sklearn
import pandas as pd
import numpy as np
from typing import Tuple, Optional, List, Dict
from src.logger import logging

def get_mlflow_credentials() -> Tuple[str, str]:
    """Get MLflow credentials from AWS Secrets Manager"""
    
    secret_name = "mlflow-basic-auth"
    region_name = "eu-central-1"
    
    logging.info(f"Retrieving secret '{secret_name}' from Secrets Manager...")
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)
    get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    secret = get_secret_value_response["SecretString"]
    secret_dict = json.loads(secret)
    logging.info("Secret retrieved successfully.")
    return secret_dict["username"], secret_dict["password"]

def setup_mlflow():
    """Setup MLflow connection"""
    username, password = get_mlflow_credentials()
    os.environ['MLFLOW_TRACKING_USERNAME'] = username
    os.environ['MLFLOW_TRACKING_PASSWORD'] = password
    
    mlflow_uri = os.environ.get('MLFLOW_TRACKING_URI')
    if not mlflow_uri:
        raise ValueError("MLFLOW_TRACKING_URI environment variable is not set.")
    mlflow.set_tracking_uri(mlflow_uri)
    logging.info(f"MLflow tracking URI set to: {mlflow_uri}")

def load_data_from_sagemaker():
    """Load data from SageMaker input path"""
    logging.info("Loading data from SageMaker...")
    df = pd.read_csv("/opt/ml/input/data/train/combined_results.csv")
    logging.info(f"Loaded data with shape: {df.shape}")
    return df

def load_prediction_data_from_sagemaker():
    """Load data for prediction from SageMaker input path"""
    logging.info("Loading prediction data from SageMaker...")
    
    # Check if running in batch transform mode (no subfolder)
    batch_transform_path = "/opt/ml/input/data/combined_results.csv"
    training_predict_path = "/opt/ml/input/data/predict/combined_results.csv"
    
    if os.path.exists(batch_transform_path):
        # Batch transform mode - data is directly in /opt/ml/input/data/
        df = pd.read_csv(batch_transform_path)
        logging.info(f"Loaded batch transform data with shape: {df.shape}")
    elif os.path.exists(training_predict_path):
        # Training job mode - data is in /opt/ml/input/data/predict/
        df = pd.read_csv(training_predict_path)
        logging.info(f"Loaded training job prediction data with shape: {df.shape}")
    else:
        # Fallback - try to find any csv file
        import glob
        csv_files = glob.glob("/opt/ml/input/data/**/*.csv", recursive=True)
        if csv_files:
            df = pd.read_csv(csv_files[0])
            logging.info(f"Loaded fallback data from {csv_files[0]} with shape: {df.shape}")
        else:
            raise FileNotFoundError("No csv file found in SageMaker input data directory")
    
    return df

class ModelPromotion:
    """Handles model registration and promotion logic using tags instead of stages"""
    
    def __init__(self, model_name="agglomeration-classifier", production_tag="production"):
        self.model_name = model_name
        self.production_tag = production_tag
        self.client = mlflow.MlflowClient()
    
    def get_production_model(self):
        """Get current production model and its metrics using tags"""
        try:
            # Search for models with production tag
            model_versions = self.client.search_model_versions(
                filter_string=f"name='{self.model_name}' and tag.{self.production_tag}='true'"
            )
            
            if model_versions:
                # Get the latest production model (highest version number)
                prod_version = max(model_versions, key=lambda x: int(x.version))
                
                # Get production model metrics
                run = self.client.get_run(prod_version.run_id)
                prod_f1 = run.data.metrics.get("test_avg_f1", 0.0)
                logging.info(f"Found production model version {prod_version.version} with F1: {prod_f1}")
                return prod_version, prod_f1
            else:
                logging.info("No production model found")
                return None, None
        except Exception as e:
            logging.warning(f"Error retrieving production model: {e}")
            return None, None
    
    def remove_production_tag_from_all(self):
        """Remove production tag from all existing models"""
        try:
            # Find all models with production tag
            production_models = self.client.search_model_versions(
                filter_string=f"name='{self.model_name}' and tag.{self.production_tag}='true'"
            )
            
            for model_version in production_models:
                logging.info(f"Removing production tag from version {model_version.version}")
                self.client.delete_model_version_tag(
                    name=self.model_name,
                    version=model_version.version,
                    key=self.production_tag
                )
        except Exception as e:
            logging.warning(f"Error removing production tags: {e}")
    
    def promote_to_production(self, model_version, reason):
        """Promote a model to production by tagging it"""
        # First remove production tag from all existing models
        self.remove_production_tag_from_all()
        
        # Tag the new model as production
        self.client.set_model_version_tag(
            name=self.model_name,
            version=model_version.version,
            key=self.production_tag,
            value="true"
        )
        
        # Add promotion metadata
        self.client.set_model_version_tag(
            name=self.model_name,
            version=model_version.version,
            key="promotion_reason",
            value=reason
        )
        
        self.client.set_model_version_tag(
            name=self.model_name,
            version=model_version.version,
            key="promoted_at",
            value=pd.Timestamp.now().isoformat()
        )
        
        logging.info(f"Promoted model version {model_version.version} to production")
    
    def compare_and_promote(self, new_model_uri, new_f1, run_id):
        """Compare new model with production and handle promotion"""
        prod_model, prod_f1 = self.get_production_model()
        
        # Register the new model first
        model_version = mlflow.register_model(
            model_uri=new_model_uri,
            name=self.model_name
        )
        
        # Add basic tags to the new model
        self.client.set_model_version_tag(
            name=self.model_name,
            version=model_version.version,
            key="created_at",
            value=pd.Timestamp.now().isoformat()
        )
        
        self.client.set_model_version_tag(
            name=self.model_name,
            version=model_version.version,
            key="test_f1_score",
            value=str(new_f1)
        )
        
        logging.info(f"Registered model version {model_version.version}")
        
        # Case 1: No production model exists
        if prod_model is None:
            reason = "First production model (no existing prod model)"
            logging.info("No production model exists. Promoting new model to production by default.")
            self.promote_to_production(model_version, reason)
            return True, reason
        
        # Case 2: Production model exists - compare performance
        try:
            # Use the correct URI format for loading production model by version
            prod_model_uri = f"models:/{self.model_name}/{prod_model.version}"
            logging.info(f"Attempting to load production model from: {prod_model_uri}")
            
            prod_model_loaded = mlflow.sklearn.load_model(model_uri=prod_model_uri)
            logging.info("Successfully loaded production model for comparison")
            
            # If we can load it successfully, compare F1 scores
            if new_f1 >= prod_f1:
                reason = f"F1 improved: {prod_f1:.4f} -> {new_f1:.4f}"
                logging.info(f"New model F1 ({new_f1:.4f}) >= Production F1 ({prod_f1:.4f}). Promoting to production.")
                self.promote_to_production(model_version, reason)
                return True, f"Promoted ({reason})"
            else:
                reason = f"F1 not improved: {prod_f1:.4f} -> {new_f1:.4f}"
                logging.info(f"New model F1 ({new_f1:.4f}) < Production F1 ({prod_f1:.4f}). Not promoting.")
                
                # Tag as candidate but not production
                self.client.set_model_version_tag(
                    name=self.model_name,
                    version=model_version.version,
                    key="candidate",
                    value="true"
                )
                
                return False, f"Not promoted ({reason})"
                
        except Exception as e:
            # Case 3: Error loading production model (dimension mismatch, etc.)
            reason = f"Production model error: {str(e)[:100]}"
            logging.warning(f"Error loading production model: {e}. Promoting new model regardless of performance.")
            self.promote_to_production(model_version, reason)
            return True, f"Promoted ({reason})"

def load_production_model():
    """
    Load the current production model from the MLflow Model Registry.

    Returns:
        model: The loaded machine learning model (e.g., scikit-learn model).
        prod_model: Metadata about the production model (e.g., version, run ID).
    """
    logging.info("Loading production model...")

    promotion = ModelPromotion()

    prod_model, prod_f1 = promotion.get_production_model()

    if prod_model is None:
        raise ValueError("No production model found! Train a model first.")

    model_uri = f"models:/agglomeration-classifier/{prod_model.version}"
    logging.info(f"Loading production model from: {model_uri}")

    model = mlflow.sklearn.load_model(model_uri)
    logging.info(f"Successfully loaded production model (version {prod_model.version}, F1: {prod_f1:.4f})")

    return model, prod_model