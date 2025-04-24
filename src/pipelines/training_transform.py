"""
Module for orchestrating the training transformation process.

This module integrates multiple components, including data management,
data transformation, OpenFOAM simulation handling, and data splitting.
It defines a main function, `training_transform`, which performs these
steps and returns the processed training and testing data.
"""
import os
from src.utility import get_root
from src.components.data_management import DataManagement
from src.components.data_transformation import transform_data
from src.components.openfoam_handler import OpenFoamHandler


def training_transform():
    """
    Main function to handle the training transformation process.

    This function orchestrates the data management, OpenFOAM simulation,
    data transformation, and data splitting tasks.

    Returns:
        TrainTestData: A dataclass containing the split data and feature names.
    """
    data_management = DataManagement()
    df, version_id = data_management.initiate_data_ingestion()

    transformed_data = transform_data(df)
    transformed_data = transformed_data.head(2)
    openfoam_handler = OpenFoamHandler(transformed_data)
    simulation_results = openfoam_handler.simulate()

    path = os.path.join(get_root(), "data", "processed", "processed_data.xlsx")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    simulation_results.to_excel(path)
    data_management.upload_excel(path, "aimfiltech-bucket", "processed/processed_data.xlsx", version_id)


if __name__ == "__main__":
    training_transform()