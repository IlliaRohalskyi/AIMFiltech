"""
This module defines the OpenFOAM ETL pipeline using Prefect tasks.
"""

from prefect import flow, task

from src.components.openfoam_handler import OpenfoamHandler


@task(name="Extract Data")
def extract(openfoam_handler: OpenfoamHandler):
    """
    Extracts results from OpenFOAM simulation using the provided OpenfoamHandler object.

    Args:
        openfoam_handler (OpenfoamHandler): Instance of the OpenfoamHandler class.

    Returns:
        dict: Dictionary containing DataFrames with extracted results.
    """
    return openfoam_handler.extract_result()


@task(name="Transform Data")
def transform(openfoam_handler: OpenfoamHandler, extracted_data):
    """
    Transforms the extracted results using the provided OpenfoamHandler object.

    Args:
        openfoam_handler (OpenfoamHandler): Instance of the OpenfoamHandler class.
        extracted_data (dict): Dictionary containing DataFrames with extracted results.

    Returns:
        pandas.DataFrame: Combined DataFrame with transformed results.
    """
    return openfoam_handler.transform_result(extracted_data)


@task(name="Load Data")
def load(openfoam_handler: OpenfoamHandler, transformed_data):
    """
    Loads the transformed results using the provided OpenfoamHandler object.

    Args:
        openfoam_handler (OpenfoamHandler): Instance of the OpenfoamHandler class.
        transformed_data (pandas.DataFrame): Combined DataFrame with transformed results.
    """
    openfoam_handler.load_result(transformed_data)


@flow(name="OpenFOAM ETL Pipeline")
def openfoam_etl_pipeline():
    """
    Defines the OpenFOAM ETL pipeline using the extract, transform, and load tasks.
    """
    handler = OpenfoamHandler()
    extracted_data = extract(handler)
    transformed_data = transform(handler, extracted_data)
    load(handler, transformed_data)


if __name__ == "__main__":
    openfoam_etl_pipeline()
