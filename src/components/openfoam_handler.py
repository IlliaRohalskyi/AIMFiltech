"""
Module for handling OpenFOAM simulations and result processing.

This module provides a class `OpenFoamHandler` to manage OpenFOAM simulations.
"""

import glob
import os
import subprocess
import pandas as pd

from src.logger import logging
from src.utility import get_cfg, get_root


class OpenFoamHandler: # pylint: disable=R0903
    """
    Class to handle OpenFOAM simulations and result processing.
    This class manages the simulation process, including
    running the OpenFOAM solver, and extracting results.
    """

    def __init__(self, input_df: pd.DataFrame):
        """
        Initialize the OpenFoamHandler instance.
        This method sets up the case path, input data, and configuration settings.
        Args:
            input_df (pd.DataFrame): A DataFrame containing simulation input data.
                                     Must include columns "UIn" and "p".
        """
        self.case_path = os.path.join(get_root(), "openfoam_case")
        self.input_df = input_df
        self.config = get_cfg("components/openfoam_handler.yaml")

    def simulate(self) -> pd.DataFrame:
        """
        Run OpenFOAM simulations for the provided input data.
        This method processes each row of the input DataFrame, runs the OpenFOAM simulation,
        and appends the results as new columns to the DataFrame.

        Returns:
            pd.DataFrame: A DataFrame containing the input data along with simulation results.
        """
        logging.info("Processing simulations")

        main_params_dict = self.config["main"]
        output_dict = self.config["simulation_output"]

        results_df = self.input_df.copy()

        for index, row in self.input_df.iterrows():
            logging.info(f"Processing simulation for row {index}")
            result = self._process_variant(index, row, main_params_dict, output_dict)
            for key, value in result.items():
                results_df.loc[index, key] = value

        logging.info(
            "Processing simulations completed. Initiating cleanup and"
            "saving results to a variable"
        )

        self._cleanup()

        return results_df

    def _process_variant(self, index, row, main_params_dict, output_dict) -> dict: #pylint: disable=R0914
        """
        Process a single simulation variant.

        Args:
            index: Index of the row being processed.
            row: A row from the DataFrame containing input data for the simulation.
            main_params_dict: Configuration parameters for the simulation.
            output_dict: Dictionary specifying output file paths and keys.

        Returns:
            dict: A dictionary containing the simulation results.
        """
        logging.info(f"Processing Variant with ID: {index}")
        logging.info("Generating parameter file")
        parameter_file_name = f"{main_params_dict['name']}_variant_{index}.txt"

        with open(parameter_file_name, "w", encoding="utf-8") as parameter_file:
            for key, value in row.items():
                line = f"{key} {value};\n"
                parameter_file.write(line)

        subprocess.run(["pyFoamClearCase.py", self.case_path], check=True)
        parameter_arg = f"--parameter-file={parameter_file_name}"
        subprocess.run(["pyFoamPrepareCase.py", self.case_path, parameter_arg], check=True)
        os.remove(parameter_file_name)

        logging.info("Running OpenFOAM simulation")
        mesher = main_params_dict["mesher"]
        solver = main_params_dict["solver"]
        subprocess.run([mesher, "-case", self.case_path], check=True)
        subprocess.run([solver, "-case", self.case_path], check=True)

        logging.info("Simulation completed. Extracting results")

        output_results = {}
        for key, value in output_dict.items():
            output_file_path = self.case_path + value

            with open(output_file_path, encoding="utf-8") as result_file:
                for line in result_file:
                    pass
                last_line = line.strip()

            output_values = last_line.split()

            for idx, val in enumerate(output_values):
                if idx == 0:
                    continue
                formatted_key = f"OUT_{key}_{idx}"
                output_results[formatted_key] = val

        return output_results

    def _cleanup(self):
        """
        Cleanup temporary files generated during the simulation.
        """
        subprocess.run(["pyFoamClearCase.py", self.case_path], check=True)

        rm_string_1 = os.path.join(self.case_path, "PyFoam*")
        for filename in glob.glob(rm_string_1):
            os.remove(filename)

        rm_string_2 = os.path.join(self.case_path, "openfoam_case.foam")
        try:
            os.remove(rm_string_2)
        except OSError:
            pass

        rm_string_3 = os.path.join(self.case_path, "test_openfoam_case.foam")
        try:
            os.remove(rm_string_3)
        except OSError:
            pass
