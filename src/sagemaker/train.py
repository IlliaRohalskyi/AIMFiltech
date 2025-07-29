import json
import os
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
import warnings
warnings.filterwarnings('ignore')
from src.logger import logging
from src.components.mlflow_utils import setup_mlflow, load_data_from_sagemaker, ModelPromotion

@dataclass
class TrainTestData:
    x_train: np.ndarray
    x_test: np.ndarray
    y_train: np.ndarray
    y_test: np.ndarray
    feature_names: list

class ModelTrainer:
    def upload_baseline_stats(self):
        """Calculate and upload baseline statistics as MLflow artifact"""
        logging.info("Saving baseline statistics as MLflow artifact...")
        stats = {
            'mean': np.mean(self.data.x_train, axis=0).tolist(),
            'std': np.std(self.data.x_train, axis=0).tolist(),
            'min': np.min(self.data.x_train, axis=0).tolist(),
            'max': np.max(self.data.x_train, axis=0).tolist(),
            'shape': list(self.data.x_train.shape),
            'feature_names': self.data.feature_names,
            'timestamp': pd.Timestamp.now().isoformat()
        }

        os.makedirs("artifacts", exist_ok=True)
        stats_path = "artifacts/baseline_stats.json"
        with open(stats_path, "w") as f:
            json.dump(stats, f, indent=2)

        mlflow.log_artifact(stats_path)

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
        logging.info("Setting up MLflow...")
        setup_mlflow()
                
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
            
            # Save baseline statistics as MLflow artifact for future monitoring
            self.upload_baseline_stats()
            
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
    df = load_data_from_sagemaker()
    
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

def run_training():
    """Main training function to be called by __main__.py"""    
    logging.info("=== Starting training process ===")
    
    try:
        data = load_data()
        trainer = ModelTrainer(data)
        trainer.train_and_log()
        logging.info("=== Training completed successfully ===")
    except Exception as e:
        logging.error(f"Training failed with error: {e}")
        raise

if __name__ == "__main__":
    run_training()