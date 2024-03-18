"""
Utility Module.

Provides utility functions

Example:
    from src.utility import get_cfg()
    config_file = get_cfg("logger.yaml")
    print(f"The logger path is: {config_file['path']}")
"""

import os

import yaml


def get_cfg(cfg_path, encoding="utf-8") -> dict:
    """
    Loads a YAML configuration file from the specified path.

    Args:
        cfg_path (str): The path to the YAML configuration file from the .cfg directory.
        encoding (str, optional): The encoding to use when reading the file. Defaults to "utf-8".

    Returns:
        dict: The YAML configuration file.
    """
    root_path = get_root()

    absolute_path = os.path.join(root_path, ".cfg", cfg_path)

    with open(absolute_path, encoding=encoding) as file:
        return yaml.safe_load(file)


def get_root() -> str:
    """
    Get Project Root Directory.

    This function determines the root directory of a project based on the location of the script.
    It navigates upwards in the directory tree until it finds the setup.py file.

    Returns:
        str: The absolute path of the project's root directory.
    """
    script_path = os.path.abspath(__file__)

    # Navigate upwards in the directory tree until you find the setup.py file
    while not os.path.exists(os.path.join(script_path, "setup.py")):
        script_path = os.path.dirname(script_path)

    return script_path
