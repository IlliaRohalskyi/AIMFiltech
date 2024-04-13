"""
This module provides a class for handling OpenFOAM simulations and
result processing, including extraction, transformation, and loading of results.
"""

import os

import pandas as pd
from PyFoam.Applications.Runner import Runner

from src.utility import get_cfg, get_root


class OpenfoamHandler:
    """
    Class to handle OpenFOAM simulations and results processing.

    Attributes:
        config (dict): Configuration settings loaded from YAML file.
    """

    def __init__(self):
        """
        Initialize the OpenfoamHandler class.
        """
        self.config = get_cfg("components/openfoam_handler.yaml")

    def launch_simulation(self):
        """
        Launch the OpenFOAM simulation.
        """
        case_name = self.config["case_name"]
        solver = self.config["solver_name"]
        Runner(args=[solver, "-case", case_name])

    def extract_result(self):
        """
        Extract results from .dat files and return as a dictionary of DataFrames.

        Returns:
            dict: Dictionary containing DataFrames with results from .dat files.
        """
        dat_paths = self.config["read_dat_paths"]
        skiprows = self.config["read_skiprows"]
        dat_dataframes = {}
        for dat_path in dat_paths:
            df = pd.read_csv(
                os.path.join(get_root(), dat_path), delimiter="\t", skiprows=skiprows
            )
            print(os.path.splitext(os.path.basename(dat_path)))
            split_path = dat_path.split("/")
            value_name = split_path[split_path.index("postProcessing") + 1]
            dat_dataframes[value_name] = df
        return dat_dataframes

    def transform_result(self, dat_results):
        """
        Transform the extracted results and return as a combined DataFrame.

        Args:
            dat_results (dict): Dictionary of DataFrames containing extracted results.

        Returns:
            pandas.DataFrame: Combined DataFrame with transformed results.
        """
        replace_col = self.config["replace_col_name"]
        for value_name, dat_df in dat_results.items():
            dat_df.columns = dat_df.columns.str.replace("#", "").str.strip()
            dat_df.rename(columns={replace_col: value_name}, inplace=True)

        combined_df = pd.concat(dat_results.values(), axis=1)
        return combined_df.loc[:, ~combined_df.columns.duplicated()]

    def load_result(self, dat_result):
        """
        Load the transformed result into a CSV file, appending to existing data if file exists.

        Args:
            dat_result (pandas.DataFrame): Transformed result DataFrame.
        """
        folder_name = self.config["data_folder"]
        folder_path = os.path.join(get_root(), folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        file_name = self.config["file_name"]
        file_path = os.path.join(folder_path, file_name)

        if os.path.exists(file_path):
            existing_data = pd.read_csv(file_path)
            max_label = existing_data["experiment"].max()
            experiment_label = max_label + 1
            dat_result["experiment"] = experiment_label
            updated_data = pd.concat([existing_data, dat_result], ignore_index=True)
        else:
            dat_result["experiment"] = 1
            updated_data = dat_result

        updated_data.to_csv(file_path, index=False)
