"""
Integration test module for the OpenFOAM ETL pipeline.
"""

import shutil

from src.components.openfoam_handler import OpenFoamHandler
from src.utility import get_cfg


def test_integration():
    """
    Test the integration of the OpenFOAM ETL pipeline.

    This function performs a test of the OpenFOAM ETL pipeline, including extraction,
    transformation, and loading of data.
    """
    handler = OpenFoamHandler()
    config = get_cfg("test/integration/openfoam_etl_pipeline.yaml")
    handler.config = config

    extracted_data = handler.extract_result()
    transformed_data = handler.transform_result(extracted_data)
    handler.load_result(transformed_data)

    shutil.rmtree(config["data_folder"])
