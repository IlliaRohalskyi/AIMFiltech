import os
from dataclasses import dataclass
from typing import List

import boto3
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from src.logger import logging


@dataclass
class TrainTestData:
    """
    Container for training and testing data along with feature names.
    """

    x_train: np.ndarray
    y_train: np.ndarray
    x_test: np.ndarray
    y_test: np.ndarray
    feature_names: List[str]


def transform_and_split_data( # pylint: disable=R0914
    df: pd.DataFrame,
) -> TrainTestData:
    """
    Transforms the dataframe and splits it into training and testing data.

    Args:
        df (pd.DataFrame): The input dataframe.

    Returns:
        TrainTestData: A dataclass containing the split data and feature names.
    """
    logging.info("Starting data transformation")

    df.columns = df.iloc[0]
    df = df[1:].reset_index(drop=True)
    
    expanded_data = []

    for i in range(0, len(df), 3):
        feed = df.iloc[i, 2:9].values
        permeat = df.iloc[i + 1, 2:9].values
        retentat = df.iloc[i + 2, 2:9].values
        sample_value = int(df.iloc[i + 2, 9])
        expanded_data.append(
            list(feed) + list(permeat) + list(retentat) + [sample_value]
        )

    columns = [
        f"{label}_{col}"
        for label in ["Feed", "Permeat", "Retentat"]
        for col in df.columns[2:9]
    ] + ["Agglomeration class"]

    expanded_df = pd.DataFrame(expanded_data, columns=columns)

    logging.info("Data transformation completed successfully")

    features = expanded_df.drop(columns=["Agglomeration class"])
    target = expanded_df["Agglomeration class"]
    feature_names = features.columns.tolist()

    logging.info("Splitting data into training and testing sets")
    x_train, x_test, y_train, y_test = train_test_split(
        features.values, target.values, test_size=0.2, random_state=42
    )

    logging.info("Data splitting completed successfully")

    return TrainTestData(
        x_train=x_train,
        y_train=y_train,
        x_test=x_test,
        y_test=y_test,
        feature_names=feature_names,
    )

if __name__ == "__main__":
    from src.utility import get_root
    from src.components.data_management import DataManagement

    data_management = DataManagement()
    df = data_management.initiate_data_ingestion()
    train_test_data = transform_and_split_data(df)
    
    # Train Logistic Regression model
    model = LogisticRegression(max_iter=200)  # Increase max_iter to ensure convergence
    model.fit(train_test_data.x_train, train_test_data.y_train)
    
    # Predict and calculate accuracy
    y_pred = model.predict(train_test_data.x_test)
    accuracy = accuracy_score(train_test_data.y_test, y_pred)
    print(f"Accuracy: {accuracy}")

    # Ensure the directory exists before saving the model
    model_dir = os.path.join(get_root(), 'model')
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, 'logistic_regression_model.joblib')
    joblib.dump(model, model_path)

    # Initialize a session using your credentials and region
    session = boto3.Session(region_name='eu-central-1')
    s3_client = session.client('s3')

    bucket_name = 'aimfiltech-training-bucket'
    try:
        s3_client.upload_file(
            model_path,
            bucket_name,
            'models/logistic_regression_model.joblib',
            ExtraArgs={'ServerSideEncryption': 'AES256'}
        )
        print("Model uploaded to S3 successfully.")
    except boto3.exceptions.S3UploadFailedError as e:
        print(f"Failed to upload model to S3: {e}")

    # Register the model in SageMaker
    sagemaker_client = session.client('sagemaker')

    model_package_group_name = 'MyModelPackageGroup'
    model_package_group_desc = 'My model package group description'
    
    # Check if the model package group already exists
    try:
        sagemaker_client.describe_model_package_group(
            ModelPackageGroupName=model_package_group_name
        )
        print(f"Model Package Group '{model_package_group_name}' already exists.")
    except sagemaker_client.exceptions.ResourceNotFound:
        sagemaker_client.create_model_package_group(
            ModelPackageGroupName=model_package_group_name,
            ModelPackageGroupDescription=model_package_group_desc
        )
        print(f"Model Package Group '{model_package_group_name}' created.")

    model_package_arn = sagemaker_client.create_model_package(
        ModelPackageGroupName=model_package_group_name,
        ModelPackageDescription='Initial version of the model',
        InferenceSpecification={
            'Containers': [
                {
                    'Image': '763104351884.dkr.ecr.eu-central-1.amazonaws.com/pytorch-inference:1.9.0-cpu-py38-ubuntu20.04',  # Example public image
                    'ModelDataUrl': f's3://{bucket_name}/models/logistic_regression_model.joblib'
                }
            ],
            'SupportedContentTypes': ['application/x-joblib'],
            'SupportedResponseMIMETypes': ['application/json']
        },
        ModelApprovalStatus='Approved'
    )['ModelPackageArn']
    
    print(f"Model registered with ARN: {model_package_arn}")

    print(train_test_data)