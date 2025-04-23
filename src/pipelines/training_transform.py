"""
Module for orchestrating the training transformation process.

This module integrates multiple components, including data management,
data transformation, OpenFOAM simulation handling, and data splitting.
It defines a main function, `training_transform`, which performs these
steps and returns the processed training and testing data.
"""

from src.components.data_management import DataManagement
from src.components.data_transformation import split_data, transform_data
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
    df = data_management.initiate_data_ingestion()

    transformed_data = transform_data(df)

    openfoam_handler = OpenFoamHandler(transformed_data)
    simulation_results = openfoam_handler.simulate()

    train_test_data = split_data(simulation_results)

    return train_test_data


if __name__ == "__main__":
    result = training_transform()
    print(result)
