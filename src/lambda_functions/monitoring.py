import json
import os
import traceback
import boto3
import pandas as pd
import mlflow

from src.logger import logging
from src.components.mlflow_utils import setup_mlflow


def get_latest_run_with_baseline():
    client = mlflow.tracking.MlflowClient()

    experiment = client.get_experiment_by_name("Default")
    experiment_id = experiment.experiment_id

    runs = client.search_runs(
        experiment_ids=[experiment_id],
        filter_string="attributes.status = 'FINISHED'",
        order_by=["start_time DESC"],
        max_results=50,
    )

    for run in runs:
        try:
            files = client.list_artifacts(run.info.run_id)
            filenames = [f.path for f in files]
            if "baseline_stats.json" in filenames:
                return run.info.run_id
        except Exception as e:
            logging.warning(f"Skipping run {run.info.run_id}: {e}")

    raise Exception("No MLflow run found with baseline_stats.json artifact")

def load_baseline_stats_from_mlflow(run_id):
    with mlflow.start_run(run_id=run_id):
        local_path = mlflow.artifacts.download_artifacts(run_id=run_id, artifact_path="baseline_stats.json")
        with open(local_path, "r") as f:
            return json.load(f)

def load_prediction_data(s3_bucket, s3_key):
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=s3_bucket, Key=s3_key)
    df = pd.read_csv(obj["Body"])
    logging.info(f"Loaded prediction data: {df.shape}")
    return df


def compare_distributions(baseline_stats, pred_df, feature_names, drift_threshold=2.0):
    drifted_features = []
    drift_report = []
    for i, feat in enumerate(feature_names):
        baseline_mean = baseline_stats["mean"][i]
        baseline_std = baseline_stats["std"][i]
        pred_mean = pred_df[feat].mean()
        z_score = abs(pred_mean - baseline_mean) / (baseline_std + 1e-8) if baseline_std > 0 else 0
        logging.info(
            f"Feature: {feat}, baseline_mean: {baseline_mean}, pred_mean: {pred_mean}, z_score: {z_score}"
        )
        if z_score > drift_threshold:
            drifted_features.append(feat)
            drift_report.append(
                f"Feature '{feat}' drift: baseline_mean={baseline_mean:.3f}, "
                f"pred_mean={pred_mean:.3f}, z_score={z_score:.2f}"
            )
    return drifted_features, drift_report


def check_confidence(pred_df, threshold=0.7, ratio_threshold=0.9):
    if "Confidence" not in pred_df.columns:
        raise Exception("Prediction data missing 'Confidence' column")
    low_conf_mask = pred_df["Confidence"] < threshold
    low_conf_ratio = low_conf_mask.mean()
    logging.info(f"Low confidence ratio: {low_conf_ratio}")
    return low_conf_ratio >= ratio_threshold, low_conf_ratio


def send_sns_alert(topic_arn, subject, message):
    sns = boto3.client("sns")
    sns.publish(TopicArn=topic_arn, Subject=subject, Message=message)
    logging.info("SNS alert sent.")


def lambda_handler(event, context):
    try:
        os.environ["MLFLOW_TRACKING_INSECURE_TLS"] = "true"
        os.environ["MLFLOW_TRACKING_URI"] = event.get("mlflow_tracking_uri")
        logging.info(f"Received event: {json.dumps(event)}")

        # ✅ Authenticate and configure MLflow (same as training)
        setup_mlflow()

        s3_bucket = event["s3_bucket"]
        s3_key = event["s3_key"]
        sns_topic_arn = event["sns_topic_arn"]

        run_id = get_latest_run_with_baseline()
        logging.info(f"Baseline run ID: {run_id}")

        baseline_stats = load_baseline_stats_from_mlflow(run_id)
        if not baseline_stats or "feature_names" not in baseline_stats or baseline_stats["feature_names"] is None:
            raise Exception("Baseline stats missing or feature_names is None")
        feature_names = baseline_stats["feature_names"]

        pred_df = load_prediction_data(s3_bucket, s3_key)
        if pred_df is None or len(pred_df) == 0:
            raise Exception("Prediction data is empty or None")

        drifted_features, drift_report = compare_distributions(baseline_stats, pred_df, feature_names)
        drift_detected = len(drifted_features) > 0

        low_conf_detected, low_conf_ratio = check_confidence(pred_df, threshold=0.7, ratio_threshold=0.9)

        alerts = []
        if drift_detected:
            alerts.append("🚨 Data drift detected in features:\n" + "\n".join(drift_report))
        if low_conf_detected:
            alerts.append(
                f"🚨 Low confidence detected: {low_conf_ratio * 100:.1f}% of predictions below 70% confidence."
            )

        if alerts:
            alert_msg = "\n\n".join(alerts)
            send_sns_alert(sns_topic_arn, "ML Monitoring Alert", alert_msg)
            logging.warning("Monitoring alert sent:\n" + alert_msg)
        else:
            logging.info("No drift or low confidence detected.")

        return {
            "statusCode": 200,
            "drift_detected": bool(drift_detected),
            "drifted_features": drifted_features,
            "low_confidence_detected": bool(low_conf_detected),
            "low_confidence_ratio": float(low_conf_ratio),
            "alerts": alerts
        }

    except Exception as e:
        logging.error(f"Monitoring failed: {e}")
        logging.error(traceback.format_exc())
        raise
