"""
This module defines the OpenFOAM pipeline
"""

from prefect import flow, task

from src.components.openfoam_handler import OpenFoamHandler


@task
def generate_variants(handler):
    """
    Generates the variants for the OpenFOAM pipeline
    """
    handler.generate_variants()


@task
def process_variants_file(handler):
    """
    Processes the variants file for the OpenFOAM pipeline
    """
    handler.process_variants_file()


@flow(name="OpenFOAM pipeline")
def openfoam_pipeline():
    """
    Defines the OpenFOAM ETL pipeline using the extract, transform, and load tasks.
    """
    handler = OpenFoamHandler()
    generate_variants(handler)
    process_variants_file(handler)


if __name__ == "__main__":
    openfoam_pipeline()
