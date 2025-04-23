"""
Module for Data Transformation and Splitting.

This module provides functionality to transform raw experimental data into a structured
format suitable for machine learning and to split the data into training and testing sets.
"""

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd
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


def transform_data(  # pylint: disable=R0914
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
    df = df[1:].reset_index(drop=True)

    expanded_data = []

    for i in range(0, len(df), 3):
        feed = df.iloc[i, 2:11].values
        permeat = df.iloc[i + 1, 2:11].values
        retentat = df.iloc[i + 2, 2:11].values
        sample_value = int(df.iloc[i + 2, 11])
        expanded_data.append(
            list(feed) + list(permeat) + list(retentat) + [sample_value]
        )

    columns = [
        f"{label}_{col}"
        for label in ["Feed", "Permeat", "Retentat"]
        for col in df.columns[2:11]
    ] + [df.columns[11]]

    expanded_df = pd.DataFrame(expanded_data, columns=columns)
    expanded_df.rename(
        columns={
            "Feed_Velocity Input Sim l/min": "UIn",
            "Feed_Pressure Input Sim bar": "p",
        },
        inplace=True,
    )

    logging.info("Data transformation completed successfully")

    return expanded_df


def split_data(transformed_data: pd.DataFrame) -> TrainTestData:
    """
    Splits the transformed data into training and testing sets.

    Args:
        transformed_data (pd.DataFrame): The transformed data.

    Returns:
        TrainTestData: A dataclass containing the split data and feature names.
    """
    logging.info("Splitting data into training and testing sets")

    features = transformed_data.drop(columns=["Agglomeration class"])
    target = transformed_data["Agglomeration class"]
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
