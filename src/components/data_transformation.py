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

def transform_data(  # pylint: disable=R0914
    df: pd.DataFrame,
):
    """
    Transforms the dataframe and splits it into training and testing data.

    Args:
        df (pd.DataFrame): The input dataframe.

    Returns:
        pd.DataFrame: The transformed dataframe with or without target column.
    """
    logging.info("Starting data transformation")
    df = df[1:].reset_index(drop=True)

    expanded_data = []

    for i in range(0, len(df), 3):
        feed = df.iloc[i, 2:11].values
        permeat = df.iloc[i + 1, 2:11].values
        retentat = df.iloc[i + 2, 2:11].values
        
        # Check if target column exists (training data) or not (prediction data)
        row_data = list(feed) + list(permeat) + list(retentat)
        if len(df.columns) > 11 and pd.notna(df.iloc[i + 2, 11]):
            sample_value = int(df.iloc[i + 2, 11])
            row_data.append(sample_value)
        
        expanded_data.append(row_data)

    # Create column names
    columns = [
        f"{label}_{col}"
        for label in ["Feed", "Permeat", "Retentat"]
        for col in df.columns[2:11]
    ]
    
    # Add target column name only if we have target data
    if len(df.columns) > 11:
        columns.append(df.columns[11])

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