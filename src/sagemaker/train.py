import os
os.environ["AWS_REGION"] = "eu-central-1"
os.environ["AWS_DEFAULT_REGION"] = "eu-central-1"
os.environ["AWS_STS_REGIONAL_ENDPOINTS"] = "regional"
os.environ["MLFLOW_TRACKING_INSECURE_TLS"] = "true"
os.environ["MLFLOW_HTTP_REQUEST_TIMEOUT"] = "60" 
os.environ["MLFLOW_HTTP_REQUEST_MAX_RETRIES"] = "5"
os.environ["MLFLOW_HTTP_REQUEST_BACKOFF_FACTOR"] = "2"

import pandas as pd
import numpy as np
import mlflow
import mlflow.sklearn
from mlflow.models.signature import infer_signature
import optuna
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, accuracy_score, precision_score, recall_score, confusion_matrix, classification_report
from sklearn.model_selection import train_test_split, StratifiedKFold
from dataclasses import dataclass
import boto3
import json
import socket
import time
import warnings
warnings.filterwarnings('ignore')

# Use proper logging
from src.logger import logging

@dataclass
class TrainTestData:
    x_train: np.ndarray
    x_test: np.ndarray
    y_train: np.ndarray
    y_test: np.ndarray
    feature_names: list

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

class ModelTrainer:
    def __init__(self, data: TrainTestData):
        logging.info("Initializing ModelTrainer...")
        self.data = data
        self.label_names = sorted(np.unique(np.concatenate([data.y_train, data.y_test])))
        logging.info(f"Found {len(self.label_names)} classes: {self.label_names}")

    def objective(self, trial):
        logging.info("Starting Optuna trial...")
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 2, 10),
            "max_depth": trial.suggest_int("max_depth", 2, 5),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 30),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 15),
            "max_features": trial.suggest_float("max_features", 0.1, 1),
            "bootstrap": trial.suggest_categorical("bootstrap", [True, False]),
            "random_state": 42,
        }
        
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        f1_scores = []
        for fold, (train_idx, val_idx) in enumerate(skf.split(self.data.x_train, self.data.y_train)):
            x_tr, x_val = self.data.x_train[train_idx], self.data.x_train[val_idx]
            y_tr, y_val = self.data.y_train[train_idx], self.data.y_train[val_idx]
            model = RandomForestClassifier(**params)
            model.fit(x_tr, y_tr)
            preds = model.predict(x_val)
            f1 = f1_score(y_val, preds, average='macro')
            f1_scores.append(f1)
        mean_f1 = np.mean(f1_scores)
        logging.info(f"Trial completed with mean F1: {mean_f1:.4f}")
        return mean_f1

    def create_visualizations(self, model, y_true, y_pred):
        """Create comprehensive visualizations"""
        logging.info("Creating visualizations...")
        os.makedirs("artifacts", exist_ok=True)
        
        # 1. Feature Importance Plot
        self.feature_importance_plot(model)
        
        # 2. Confusion Matrix
        self.confusion_matrix_plot(y_true, y_pred)
        
        # 3. Classification Report Heatmap
        self.classification_report_plot(y_true, y_pred)
        
        # 4. Class Distribution Plot
        self.class_distribution_plot()
        
        # 5. Model Performance Summary
        self.performance_summary_plot(y_true, y_pred)

    def feature_importance_plot(self, model):
        logging.info("Creating feature importance plot...")
        importances = model.feature_importances_
        indices = np.argsort(importances)[::-1]
        
        plt.figure(figsize=(12, 8))
        plt.title("Random Forest Feature Importance")
        
        # Create horizontal bar plot
        y_pos = np.arange(len(self.data.feature_names))
        plt.barh(y_pos, importances[indices[::-1]], alpha=0.7)
        plt.yticks(y_pos, [self.data.feature_names[i] for i in indices[::-1]])
        plt.xlabel("Feature Importance")
        plt.tight_layout()
        plt.savefig("artifacts/feature_importance.png", dpi=300, bbox_inches='tight')
        plt.close()

    def confusion_matrix_plot(self, y_true, y_pred):
        logging.info("Creating confusion matrix...")
        cm = confusion_matrix(y_true, y_pred)
        
        plt.figure(figsize=(10, 8))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                   xticklabels=self.label_names, 
                   yticklabels=self.label_names)
        plt.title('Confusion Matrix')
        plt.xlabel('Predicted Label')
        plt.ylabel('True Label')
        plt.tight_layout()
        plt.savefig("artifacts/confusion_matrix.png", dpi=300, bbox_inches='tight')
        plt.close()

    def classification_report_plot(self, y_true, y_pred):
        logging.info("Creating classification report heatmap...")
        report = classification_report(y_true, y_pred, target_names=self.label_names, output_dict=True)
        
        # Convert to DataFrame for easier plotting
        df_report = pd.DataFrame(report).iloc[:-1, :-1].T  # Remove support and avg rows

        df_report = df_report.drop(['accuracy', 'macro avg'], errors='ignore')
        df_report = df_report.drop('support', axis=1, errors='ignore')

        plt.figure(figsize=(10, 6))
        sns.heatmap(df_report, annot=True, 
                cmap='viridis',  # Sequential colormap: dark (bad) to bright (good)
                vmin=0, vmax=1,  # Explicit range from 0 to 1
                fmt='.3f', 
                cbar_kws={'label': 'Performance Score'})
        plt.title('Classification Report Heatmap')
        plt.tight_layout()
        plt.savefig("artifacts/classification_report.png", dpi=300, bbox_inches='tight')
        plt.close()

    def class_distribution_plot(self):
        logging.info("Creating class distribution plot...")
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Training set distribution
        unique_train, counts_train = np.unique(self.data.y_train, return_counts=True)
        ax1.pie(counts_train, labels=unique_train, autopct='%1.1f%%', startangle=90)
        ax1.set_title('Training Set Class Distribution')
        
        # Test set distribution  
        unique_test, counts_test = np.unique(self.data.y_test, return_counts=True)
        ax2.pie(counts_test, labels=unique_test, autopct='%1.1f%%', startangle=90)
        ax2.set_title('Test Set Class Distribution')
        
        plt.tight_layout()
        plt.savefig("artifacts/class_distribution.png", dpi=300, bbox_inches='tight')
        plt.close()

    def performance_summary_plot(self, y_true, y_pred):
        logging.info("Creating performance summary...")
        # Calculate metrics per class
        precision_per_class = precision_score(y_true, y_pred, average=None, labels=self.label_names)
        recall_per_class = recall_score(y_true, y_pred, average=None, labels=self.label_names)
        f1_per_class = f1_score(y_true, y_pred, average=None, labels=self.label_names)
        
        # Create DataFrame
        metrics_df = pd.DataFrame({
            'Precision': precision_per_class,
            'Recall': recall_per_class,
            'F1-Score': f1_per_class
        }, index=self.label_names)
        
        # Plot
        plt.figure(figsize=(12, 6))
        metrics_df.plot(kind='bar', ax=plt.gca())
        plt.title('Performance Metrics by Class')
        plt.xlabel('Class')
        plt.ylabel('Score')
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig("artifacts/performance_summary.png", dpi=300, bbox_inches='tight')
        plt.close()

    def calculate_comprehensive_metrics(self, y_true, y_pred):
        """Calculate and return comprehensive metrics"""
        metrics = {
            "test_accuracy": accuracy_score(y_true, y_pred),
            "test_avg_f1": f1_score(y_true, y_pred, average='macro'),
            "test_weighted_f1": f1_score(y_true, y_pred, average='weighted'),
            "test_avg_precision": precision_score(y_true, y_pred, average='macro'),
            "test_weighted_precision": precision_score(y_true, y_pred, average='weighted'),
            "test_avg_recall": recall_score(y_true, y_pred, average='macro'),
            "test_weighted_recall": recall_score(y_true, y_pred, average='weighted'),
        }
        
        # Per-class metrics
        for i, label in enumerate(self.label_names):
            precision_per_class = precision_score(y_true, y_pred, average=None, labels=self.label_names)
            recall_per_class = recall_score(y_true, y_pred, average=None, labels=self.label_names)
            f1_per_class = f1_score(y_true, y_pred, average=None, labels=self.label_names)
            
            metrics[f"test_precision_class_{label}"] = precision_per_class[i]
            metrics[f"test_recall_class_{label}"] = recall_per_class[i]
            metrics[f"test_f1_class_{label}"] = f1_per_class[i]
        
        return metrics

    def train_and_log(self):
        logging.info("Fetching MLflow credentials...")
        username, password = get_mlflow_credentials()
        logging.info("Setting MLflow tracking URI...")
        os.environ['MLFLOW_TRACKING_USERNAME'] = username
        os.environ['MLFLOW_TRACKING_PASSWORD'] = password
        mlflow_uri = os.environ.get('MLFLOW_TRACKING_URI')
        if not mlflow_uri:
            raise ValueError("MLFLOW_TRACKING_URI environment variable is not set.")
        mlflow.set_tracking_uri(mlflow_uri)
        logging.info(f"MLflow tracking URI set to: {mlflow_uri}")
        
        # Initialize model promotion handler
        promotion_handler = ModelPromotion()
        
        logging.info("Starting MLflow run...")
        with mlflow.start_run():
            # Log dataset info
            mlflow.log_param("n_samples_train", len(self.data.x_train))
            mlflow.log_param("n_samples_test", len(self.data.x_test))
            mlflow.log_param("n_features", len(self.data.feature_names))
            mlflow.log_param("n_classes", len(self.label_names))
            mlflow.log_param("class_labels", self.label_names)
            
            logging.info("Starting Optuna study...")
            study = optuna.create_study(direction="maximize")
            study.optimize(self.objective, n_trials=100)
            best_params = study.best_params
            logging.info(f"Best params found: {best_params}")
            mlflow.log_params(best_params)
            
            # Log Optuna study info
            mlflow.log_metric("best_cv_f1", study.best_value)
            mlflow.log_param("n_trials", len(study.trials))
            
            logging.info("Training final model with best params...")
            model = RandomForestClassifier(**best_params, random_state=42)
            model.fit(self.data.x_train, self.data.y_train)
            
            # Predictions
            preds = model.predict(self.data.x_test)
            
            # Calculate comprehensive metrics
            metrics = self.calculate_comprehensive_metrics(self.data.y_test, preds)
            
            # Log all metrics
            for metric_name, metric_value in metrics.items():
                mlflow.log_metric(metric_name, metric_value)
                logging.info(f"{metric_name}: {metric_value:.4f}")
            
            # Create and log visualizations
            self.create_visualizations(model, self.data.y_test, preds)
            
            # Log all artifacts
            for artifact in ["feature_importance.png", "confusion_matrix.png", 
                           "classification_report.png", "class_distribution.png", 
                           "performance_summary.png"]:
                mlflow.log_artifact(f"artifacts/{artifact}")
            
            # Create model signature
            signature = infer_signature(self.data.x_train, model.predict(self.data.x_train))
            
            # Log model
            model_info = mlflow.sklearn.log_model(
                model, 
                "model",
                signature=signature,
                input_example=self.data.x_train[:5]
            )
            
            # Handle model promotion
            promoted, promotion_message = promotion_handler.compare_and_promote(
                model_info.model_uri, 
                metrics["test_avg_f1"],
                mlflow.active_run().info.run_id
            )
            
            # Log promotion info
            mlflow.log_param("promoted_to_production", promoted)
            mlflow.log_param("promotion_reason", promotion_message)
            
            logging.info("MLflow logging complete.")
            logging.info(f"Model promotion: {promotion_message}")
            logging.info(f"Final metrics: {metrics}")

def load_data():
    logging.info("Loading data...")
    df = pd.read_excel("/opt/ml/input/data/train/combined_results.xlsx")
    logging.info(f"Loaded data with shape: {df.shape}")
    
    y = df["Agglomeration class"].values
    X = df.drop(columns=["Agglomeration class"]).values
    feature_names = df.drop(columns=["Agglomeration class"]).columns.tolist()
    
    logging.info(f"Features: {len(feature_names)}")
    logging.info(f"Classes: {np.unique(y)}")
    
    x_train, x_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    logging.info(f"Train set: {x_train.shape}, Test set: {x_test.shape}")
    return TrainTestData(x_train, x_test, y_train, y_test, feature_names)

def get_mlflow_credentials(secret_name="mlflow-basic-auth", region_name="eu-central-1"):
    logging.info(f"Retrieving secret '{secret_name}' from Secrets Manager...")
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)
    get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    secret = get_secret_value_response["SecretString"]
    secret_dict = json.loads(secret)
    logging.info("Secret retrieved successfully.")
    return secret_dict["username"], secret_dict["password"]

if __name__ == "__main__":
    mlflow.config.enable_async_logging()
    
    logging.info("=== Starting training process ===")
    
    try:
        data = load_data()
        trainer = ModelTrainer(data)
        trainer.train_and_log()
        logging.info("=== Training completed successfully ===")
    except Exception as e:
        logging.error(f"Training failed with error: {e}")
        raise