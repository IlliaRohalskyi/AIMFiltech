"""
Module for handling OpenFOAM simulations and result processing.

This module provides a class `OpenFoamHandler` to manage OpenFOAM simulations,
including variant generation (manual, random, cartesian) and result processing.

Dependencies:
    - pandas: DataFrame manipulation
    - prefect: Flow management

Attributes:
    config (dict): Configuration settings loaded from YAML file.
    master_file_path (str): Path to the master Excel file.
    variant_file_path (str): Path to save variant Excel file.
    master_params (dict): Parameters extracted from the master file.
    variant_df (pd.DataFrame): DataFrame containing generated variants.
    master_excel (pd.ExcelFile): ExcelFile object for the master file.

Example:
    from src.components.openfoam_handler import OpenFoamHandler

    handler = OpenFoamHandler()
    handler.generate_variants()

"""

import itertools
import os
import random
import shutil
import subprocess
from typing import Any, Dict, List

import pandas as pd
from prefect import flow, get_run_logger

from src.utility import get_cfg, get_root


class OpenFoamHandler:
    """
    Class to handle OpenFOAM simulations and results processing.

    Attributes:
        config (dict): Configuration settings loaded from YAML file.
        master_file_path (str): Path to the master Excel file.
        variant_file_path (str): Path to the variant Excel file.
        master_params (dict): Parameters extracted from the master file.
        variant_df (pd.DataFrame): DataFrame containing generated variants.
        master_excel (pd.ExcelFile): ExcelFile object of the master file.
    """

    def __init__(self):
        """
        Initialize the OpenFoamHandler class.
        """
        self.logger = get_run_logger()
        self.config = get_cfg("components/openfoam_handler.yaml")
        self.master_file_path = os.path.join(
            get_root(), "openfoam_data", "Masterfile.xlsx"
        )
        self.variant_file_path = os.path.join(
            get_root(), "openfoam_data", "Variantfile.xlsx"
        )
        self.master_params: Dict[str, Any] = {}
        self.variant_df: pd.DataFrame = pd.DataFrame()
        self.master_excel: pd.ExcelFile = None

    def generate_variants(self):
        """
        Generate simulation variants based on the specified mode in the master file.

        This method determines the generation mode from the master file and calls
        the appropriate method to generate variants.

        Raises:
            ValueError: If an invalid generation mode is specified.
        """
        self.logger.info("Starting variant generation process")
        self._load_master_file()
        generation_mode = self.master_params["mode"]

        generation_methods = {
            "manual": self._load_manual_variants,
            "random": self._generate_random_variants,
            "cartesian": self._generate_cartesian_variants,
        }

        if generation_mode not in generation_methods:
            self.logger.error("Invalid generation mode: %s", generation_mode)
            raise ValueError(f"Invalid generation mode: {generation_mode}")

        self.logger.info("Working in %s mode", generation_mode)
        self.variant_df = generation_methods[generation_mode]()

        self._save_variant_file()
        self.logger.info("Variant generation process completed successfully")

    def _load_master_file(self):
        """
        Load and parse the Masterfile.

        This method reads the master Excel file and extracts the main parameters.
        """
        self.logger.info("Loading master file: %s", self.master_file_path)
        self.master_excel = pd.ExcelFile(self.master_file_path)
        self.logger.info("Extracting master parameters")
        master_params_sheet = self.master_excel.parse("main")
        self.master_params = dict(
            zip(master_params_sheet["PARAMETER"], master_params_sheet["VALUE"])
        )
        self.logger.info(
            "Master parameters loaded: %s", list(self.master_params.keys())
        )

    def _generate_random_value(self, param_config: Dict[str, Any]) -> float:
        """
        Generate a random value based on the specified distribution.

        Args:
            param_config (dict): Configuration for the parameter.

        Returns:
            float: Generated random value.

        Raises:
            ValueError: If an invalid distribution is specified.
        """
        distribution = param_config["DISTRIBUTION"]
        if distribution == "uniform":
            return random.uniform(param_config["MIN"], param_config["MAX"])
        if distribution == "normal":
            value = random.normalvariate(param_config["MU"], param_config["SIGMA"])
            if param_config["LIMITS"] == "YES":
                value = max(param_config["MIN"], min(value, param_config["MAX"]))
            return value
        self.logger.error("Invalid distribution: %s", distribution)
        raise ValueError(f"Invalid distribution: {distribution}")

    def _generate_cartesian_values(self, param_config: Dict[str, Any]) -> List[float]:
        """
        Generate cartesian product values based on the parameter configuration.

        Args:
            param_config (dict): Configuration for the parameter.

        Returns:
            list: List of generated values.

        Raises:
            ValueError: If an invalid parameter type is specified.
        """
        param_type = param_config["TYPE"]
        if param_type == "arithmetic_progress":
            min_val, max_val, num_points = (
                param_config["MIN"],
                param_config["MAX"],
                int(param_config["N"]),
            )
            return [
                min_val + (max_val - min_val) * i / (num_points - 1)
                for i in range(num_points)
            ]
        if param_type == "geometric_progress":
            min_val, max_val, num_points = (
                param_config["MIN"],
                param_config["MAX"],
                int(param_config["N"]),
            )
            ratio = (max_val / min_val) ** (1 / (num_points - 1))
            return [min_val * ratio**i for i in range(num_points)]
        if param_type == "manual":
            return [float(value) for value in param_config["MANUAL"].split(";")]
        self.logger.error("Invalid parameter type: %s", param_type)
        raise ValueError(f"Invalid parameter type: {param_type}")

    def _load_manual_variants(self) -> pd.DataFrame:
        """
        Load manually specified variants from the master file.

        Returns:
            pd.DataFrame: DataFrame containing manual variants.
        """
        self.logger.info("Loading manual variants from master file")
        variants = self.master_excel.parse("par-manual")
        self.logger.info("Loaded %d manual variants", len(variants))
        return variants

    def _generate_random_variants(self) -> pd.DataFrame:
        """
        Generate random variants based on the configuration in the master file.

        Returns:
            pd.DataFrame: DataFrame containing generated random variants.
        """
        num_random_variants = int(self.master_params["N_random"])
        self.logger.info("Generating %d random variants", num_random_variants)
        random_params_df = self.master_excel.parse("par-random")
        variable_names = list(random_params_df["VARIABLE"])
        variants_df = pd.DataFrame(columns=["ID"] + variable_names)

        for i in range(num_random_variants):
            variant_values = [i] + [
                self._generate_random_value(random_params_df.loc[idx])
                for idx in range(len(variable_names))
            ]
            variants_df.loc[len(variants_df)] = variant_values

        self.logger.info("Generated %d random variants", len(variants_df))
        return variants_df

    def _generate_cartesian_variants(self) -> pd.DataFrame:
        """
        Generate cartesian product variants based on the configuration in the master file.

        Returns:
            pd.DataFrame: DataFrame containing generated cartesian variants.
        """
        self.logger.info("Generating cartesian product variants")
        cartesian_params_df = self.master_excel.parse("par-cartesian")
        variable_names = list(cartesian_params_df["VARIABLE"])
        variants_df = pd.DataFrame(columns=["ID"] + variable_names)

        value_lists = [
            self._generate_cartesian_values(cartesian_params_df.loc[idx])
            for idx in range(len(variable_names))
        ]

        total_combinations = 1
        for value_list in value_lists:
            total_combinations *= len(value_list)
        self.logger.info("Total combinations to generate: %d", total_combinations)

        for i, combination in enumerate(itertools.product(*value_lists)):
            variants_df.loc[len(variants_df)] = [i] + list(combination)
            if (i + 1) % 1000 == 0:
                self.logger.info("Generated %d variants", i + 1)

        self.logger.info("Generated %d cartesian variants", len(variants_df))
        return variants_df

    def _save_variant_file(self):
        """
        Save the generated variants to the Variantfile.
        """
        self.logger.info("Saving variants to %s", self.variant_file_path)
        shutil.copy(self.master_file_path, self.variant_file_path)
        with pd.ExcelWriter(
            self.variant_file_path, engine="openpyxl", mode="a"
        ) as writer:
            self.variant_df.to_excel(writer, sheet_name="variants", index=False)
        self.logger.info(
            "Variants saved successfully. Total variants: %d", len(self.variant_df)
        )

    def process_variants_file(self):
        """
        Process the Variantfile to run OpenFOAM simulations and extract results.

        This method reads the Variantfile, generates parameter files, executes
        OpenFOAM simulations for each variant, and saves results to Resultfile.

        It uses subprocesses to run external scripts and logs progress at each step.
        """
        self.logger.info("Processing Variantfile")
        variant_excel = pd.ExcelFile(self.variant_file_path)

        main_params_sheet = variant_excel.parse(
            variant_excel.sheet_names[variant_excel.sheet_names.index("main")]
        )
        main_params_dict = dict(
            zip(main_params_sheet["PARAMETER"], main_params_sheet["VALUE"])
        )

        variants_sheet = variant_excel.parse(
            variant_excel.sheet_names[variant_excel.sheet_names.index("variants")]
        )
        variants_dict = variants_sheet.to_dict()
        output_data = []

        for index, variant_id in enumerate(variants_dict["ID"]):
            output_data.append(
                self._process_variant(
                    index, variant_id, variants_dict, main_params_dict
                )
            )

        self._save_results(variants_sheet, output_data)

        self.logger.info(
            "Processing Variantfile completed. Results saved to Resultfile.xlsx"
        )

    def _process_variant(self, index, variant_id, variants_dict, main_params_dict):
        self.logger.info("Processing Variant %s with ID: %s", index, variant_id)
        self.logger.info("Generating parameter file")
        parameter_file_name = f"{main_params_dict['name']}_variant_{index}.txt"

        with open(parameter_file_name, "w", encoding="utf-8") as parameter_file:
            for key in variants_dict:
                line = f"{key} {variants_dict[key][index]};\n"
                parameter_file.write(line)

        subprocess.run(["pyFoamClearCase.py", "."], check=True)
        parameter_arg = f"--parameter-file={parameter_file_name}"
        subprocess.run(["pyFoamPrepareCase.py", ".", parameter_arg], check=True)
        os.remove(parameter_file_name)
        subprocess.run(["blockMesh"], check=True)
        subprocess.run(["simpleFoam"], check=True)
        output_file = main_params_dict["output_file"]

        with open(output_file, encoding="utf-8") as result_file:
            for line in result_file:
                pass
            last_line = line
            return last_line.split()

    def _save_results(self, variants_sheet, output_data):
        results_columns = [f"OUT{index}" for index in range(len(output_data[0]))]
        results_df = pd.DataFrame(output_data, columns=results_columns)

        result_file_path = os.path.join(get_root(), "openfoam_data", "Resultfile.xlsx")
        shutil.copy(self.variant_file_path, result_file_path)
        with pd.ExcelWriter(result_file_path, engine="openpyxl", mode="a") as writer:
            pd.concat([variants_sheet, results_df], axis=1).to_excel(
                writer, sheet_name="results", index=False
            )


@flow()
def run_openfoam_handler():
    """Prefect flow to run the OpenFoamHandler."""
    handler = OpenFoamHandler()
    handler.generate_variants()


if __name__ == "__main__":
    run_openfoam_handler()
