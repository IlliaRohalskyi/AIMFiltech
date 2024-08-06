"""
This module defines the OpenFOAM pipeline
"""

from prefect import flow, task

from src.components.openfoam_handler import OpenFoamHandler


@task(name="OpenFOAM pipeline")
def openfoam_pipeline():
    """
    Defines the OpenFOAM ETL pipeline using the extract, transform, and load tasks.
    """
    print("Creating OF handler")
    handler = OpenFoamHandler()
    print("Handler created.\n Creating variants")
    handler.generate_variants()
    print("Variants created.")
    print("Running simulations")
    handler.process_variants_file()
    print("Simulation completed.")


if __name__ == "__main__":
    openfoam_pipeline()
