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
import optuna
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split, StratifiedKFold
from dataclasses import dataclass
import boto3
import json
import socket
import time

@dataclass
class TrainTestData:
    x_train: np.ndarray
    x_test: np.ndarray
    y_train: np.ndarray
    y_test: np.ndarray
    feature_names: list

class ModelTrainer:
    def __init__(self, data: TrainTestData):
        print("Initializing ModelTrainer...")
        self.data = data

    def objective(self, trial):
        print("Starting Optuna trial...")
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 2, 10),
            "max_depth": trial.suggest_int("max_depth", 2, 5),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 30),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 15),
            "max_features": trial.suggest_float("max_features", 0.1, 1),
            "bootstrap": trial.suggest_categorical("bootstrap", [True, False]),
            "random_state": 42,
        }
        print(f"Trial params: {params}")
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        f1_scores = []
        for fold, (train_idx, val_idx) in enumerate(skf.split(self.data.x_train, self.data.y_train)):
            print(f"  Training fold {fold+1}/5...")
            x_tr, x_val = self.data.x_train[train_idx], self.data.x_train[val_idx]
            y_tr, y_val = self.data.y_train[train_idx], self.data.y_train[val_idx]
            model = RandomForestClassifier(**params)
            model.fit(x_tr, y_tr)
            preds = model.predict(x_val)
            f1 = f1_score(y_val, preds, average='macro')
            print(f"    Fold {fold+1} F1: {f1}")
            f1_scores.append(f1)
        mean_f1 = np.mean(f1_scores)
        print(f"Mean F1 for trial: {mean_f1}")
        return mean_f1

    def feature_importance_plot(self, model):
        print("Plotting feature importances...")
        importances = model.feature_importances_
        plt.figure(figsize=(10, 8))
        plt.barh(self.data.feature_names, importances)
        plt.xlabel("Feature Importance")
        plt.title("Random Forest Feature Importance")
        plt.tight_layout()
        os.makedirs("artifacts", exist_ok=True)
        plt.savefig("artifacts/feature_importance.png")
        plt.close()
        print("Feature importance plot saved.")

    def train_and_log(self):
        print("Fetching MLflow credentials...")
        username, password = get_mlflow_credentials()
        print("Setting MLflow tracking URI...")
        os.environ['MLFLOW_TRACKING_USERNAME'] = username
        os.environ['MLFLOW_TRACKING_PASSWORD'] = password
        mlflow.set_tracking_uri("https://10.0.1.154")
        print("Starting MLflow run...")
        with mlflow.start_run():
            print("Starting Optuna study...")
            study = optuna.create_study(direction="maximize")
            study.optimize(self.objective, n_trials=100)
            best_params = study.best_params
            print(f"Best params found: {best_params}")
            mlflow.log_params(best_params)
            print("Training final model with best params...")
            model = RandomForestClassifier(**best_params, random_state=42)
            model.fit(self.data.x_train, self.data.y_train)
            preds = model.predict(self.data.x_test)
            avg_f1 = f1_score(self.data.y_test, preds, average='macro')
            print(f"Test avg F1: {avg_f1}")
            mlflow.log_metric("test_avg_f1", avg_f1)
            self.feature_importance_plot(model)
            mlflow.log_artifact("artifacts/feature_importance.png")
            mlflow.sklearn.log_model(model, "model")
            print("MLflow logging complete.")
            print(f"Best params: {best_params}, Test avg F1: {avg_f1}")

def load_data():
    print("Loading data...")
    df = pd.read_excel("/opt/ml/input/data/train/combined_results.xlsx")
    print("Data loaded. Preparing train/test split...")
    y = df["Agglomeration class"].values
    X = df.drop(columns=["Agglomeration class"]).values
    feature_names = df.drop(columns=["Agglomeration class"]).columns.tolist()
    x_train, x_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print("Data split complete.")
    return TrainTestData(x_train, x_test, y_train, y_test, feature_names)

def get_mlflow_credentials(secret_name="mlflow-basic-auth", region_name="eu-central-1"):
    print(f"Retrieving secret '{secret_name}' from Secrets Manager...")
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)
    get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    secret = get_secret_value_response["SecretString"]
    secret_dict = json.loads(secret)
    print("Secret retrieved.")
    return secret_dict["username"], secret_dict["password"]

if __name__ == "__main__":
#     mlflow.config.enable_async_logging()
    
#     print("Starting training process...")
#     print("###############################################")
    
#     print("Preparing to load data and train model...")
#     data = load_data()
#     trainer = ModelTrainer(data)
#     trainer.train_and_log()
    
    print("Preparing SageMaker Estimator...")
    import sagemaker
    from sagemaker.estimator import Estimator

    role = "arn:aws:iam::961341542251:role/aimfiltech-sagemaker-execution-role"
    image_uri = "961341542251.dkr.ecr.eu-central-1.amazonaws.com/aimfiltech-sagemaker:latest"
    region = "eu-central-1"
    s3_input = "s3://aimfiltech-bucket/combined/f5579fcd-d467-b558-8d07-85204e3d7e92_2cbb5ba9-056a-93a2-d00d-ac0fe584c024/"

    sess = sagemaker.Session()

    print("Configuring Estimator...")
    estimator = Estimator(
        image_uri=image_uri,
        role=role,
        instance_count=1,
        instance_type="ml.m5.large",
        volume_size=30,
        max_run=120,
        sagemaker_session=sess,
        output_path=None,
        subnets=["subnet-0f1158dbe956d993e"],
        security_group_ids=["sg-09b942418399daac6"],
    )

    inputs = {
        "train": s3_input
    }

    print("Launching SageMaker training job...")
    estimator.fit(inputs)
    print("SageMaker training job launched.")