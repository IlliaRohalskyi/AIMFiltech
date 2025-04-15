"""
Module for handling OpenFOAM simulations and result processing.

This module provides a class `OpenFoamHandler` to manage OpenFOAM simulations.
"""

import glob
import os
import subprocess
from dataclasses import asdict, dataclass
from typing import List

import pandas as pd

from src.logger import logging
from src.utility import get_cfg, get_root


@dataclass
class Input:
    """
    Class representing input data for the OpenFOAM simulation.
    """

    UIn: float #pylint: disable=C0103
    p: float


class OpenFoamHandler: # pylint: disable=R0903
    """
    Class to handle OpenFOAM simulations and result processing.
    This class manages the simulation process, including
    running the OpenFOAM solver, and extracting results.
    """

    def __init__(self, input_data: List[Input]):
        """
        Initialize the OpenFoamHandler instance.
        This method sets up the case path, input data, and configuration settings.
        Args:
            input_data (List[Input]): A list of Input objects containing simulation input.
        """
        self.case_path = os.path.join(get_root(), "openfoam_case")
        self.input_data = input_data
        self.config = get_cfg("components/openfoam_handler.yaml")

    def simulate(self):
        """
        Run OpenFOAM simulations for the provided input data.
        This method processes each variant of input data, runs the OpenFOAM simulation,
        and extracts the results.

        Returns:
            pd.DataFrame: A DataFrame containing the results of the simulations.
        """
        logging.info("Processing simulations")

        main_params_dict = self.config["main"]
        output_dict = self.config["simulation_output"]

        output_data = []

        for index, variant in enumerate(self.input_data):
            output_data.append(
                self._process_variant(index, variant, main_params_dict, output_dict)
            )

        logging.info(
            "Processing simulations completed. Initiating cleanup and"
            "saving results to a variable"
        )

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

        results_df = pd.DataFrame(output_data)

        return results_df

    def _process_variant( # pylint: disable=R0914
        self, index, variant, main_params_dict, output_dict
    ) -> List[str]:
        logging.info("Processing Variant with ID:", index)
        logging.info("Generating parameter file")
        parameter_file_name = f"{main_params_dict['name']}_variant_{index}.txt"

        with open(parameter_file_name, "w", encoding="utf-8") as parameter_file:
            for key, value in asdict(variant).items():
                line = f"{key} {value};\n"
                parameter_file.write(line)

        subprocess.run(["pyFoamClearCase.py", self.case_path], check=True)
        parameter_arg = f"--parameter-file={parameter_file_name}"
        subprocess.run(
            ["pyFoamPrepareCase.py", self.case_path, parameter_arg], check=True
        )
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
                formatted_key = f"OUT_{key}_{idx}"
                output_results[formatted_key] = val

        return output_results


if __name__ == "__main__":
    # Example usage
    input_ = [
        Input(UIn=1.0, p=101325),
        Input(UIn=2.0, p=202650),
    ]
    handler = OpenFoamHandler(input_)
    print(handler.simulate())
