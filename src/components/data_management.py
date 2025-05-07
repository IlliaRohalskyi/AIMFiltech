"""
Data Management Module.

This module provides a class with methods for data management tasks.
"""

import os
from typing import Tuple

import boto3
import pandas as pd

from src.errors.data_management_errors import (
    MultipleFilesError, UnsupportedFileTypeError
    )
from src.logger import logging
from src.utility import get_cfg


class DataManagement:
    """
    Data management class.

    This class provides methods for data management tasks.

    Attributes:
        management_config (dict): The configuration settings for data management tasks.
    """

    def __init__(self):
        """
        Initialize the DataManagement instance.

        Attributes:
            self.management_config (dict): Configuration settings for data management tasks.
        """
        self.management_config = get_cfg("components/data_management.yaml")
        self.s3_client = boto3.client("s3")

    def _get_supported_file(self) -> Tuple[str, str]:
        """
        Retrieve the supported data file from the specified S3 bucket.

        This method checks the S3 bucket for files with supported extensions
        (xls, xlsx, csv) and returns the matching file along with its version ID.
        If no supported files are found, an `UnsupportedFileTypeError` is raised.
        If more than one supported file is found, a `MultipleFilesError` is raised.

        Returns:
            tuple: (Path to the supported data file, Version ID of the file)
        """
        bucket_name = self.management_config["s3_bucket_name"]
        prefix = self.management_config["s3_ingestion_prefix"]

        response = self.s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        if "Contents" not in response:
            logging.error("No files found in the S3 bucket")
            raise UnsupportedFileTypeError(bucket_name)

        file_list = [
            obj["Key"]
            for obj in response["Contents"]
            if obj["Key"].endswith(("xls", "xlsx", "csv"))
        ]

        if not file_list:
            logging.error("No supported files found in the S3 bucket")
            raise UnsupportedFileTypeError(bucket_name)

        if len(file_list) > 1:
            logging.error(
                "Only one file of supported format (xlsx, xls, csv) "
                "should exist in the S3 bucket"
            )
            raise MultipleFilesError

        file_key = file_list[0]

        version_response = self.s3_client.list_object_versions(Bucket=bucket_name, Prefix=file_key)
        if "Versions" not in version_response:
            logging.error(f"No versioning information available for file: {file_key}")
            raise Exception("Versioning is not enabled for the S3 bucket")

        latest_version = next(
            (version for version in version_response["Versions"] if version["Key"] == file_key),
            None
        )
        if not latest_version:
            logging.error(f"No version found for file: {file_key}")
            raise Exception(f"Unable to fetch version for file: {file_key}")

        version_id = latest_version["VersionId"]

        if not os.path.exists("/tmp"):
            os.makedirs("/tmp")
        local_file_path = os.path.join("/tmp", os.path.basename(file_key))
        self.s3_client.download_file(bucket_name, file_key, local_file_path, ExtraArgs={"VersionId": version_id})

        return local_file_path, version_id

    def initiate_data_ingestion(self) -> pd.DataFrame:
        """
        Initiate the data ingestion process.

        This method triggers the ingestion of data.
        It returns the pandas dataframe.

        Returns:
            pandas.DataFrame: A DataFrame containing the managed data
        """
        logging.info("Initiating data ingestion")

        supported_file, version_id = self._get_supported_file()
        logging.info(f"File to ingest: {supported_file}, Version ID: {version_id}")

        if supported_file.endswith("csv"):
            data = pd.read_csv(supported_file, header=0)
        else:
            data = pd.read_excel(supported_file, header=0)

        logging.info("Data ingestion completed successfully")
        return data, version_id

    def load_s3_file(self, bucket: str, key: str, version_id: str = None):
        """
        Loads a file from S3, optionally with a version_id. 
        If version_id is not provided, fetches the latest version.
        Args:
            - bucket (str): The name of the S3 bucket.
            - key (str): The S3 object key.
            - version_id (str, optional): The version ID of the S3 object. Defaults to None.
        Returns:
            - If version_id is provided: pd.DataFrame
            - If version_id is None: (pd.DataFrame, version_id)
        """
        if not os.path.exists("/tmp"):
            os.makedirs("/tmp")
        local_file_path = os.path.join("/tmp", os.path.basename(key))

        if version_id is None:
            version_response = self.s3_client.list_object_versions(Bucket=bucket, Prefix=key)
            if "Versions" not in version_response:
                raise Exception("No versioning information available for file")
            latest_version = next(
                (v for v in version_response["Versions"] if v["Key"] == key),
                None
            )
            if not latest_version:
                raise Exception("Unable to fetch latest version for file")
            version_id = latest_version["VersionId"]

        self.s3_client.download_file(bucket, key, local_file_path, ExtraArgs={"VersionId": version_id})
        if key.endswith(".csv"):
            df = pd.read_csv(local_file_path)
        else:
            df = pd.read_excel(local_file_path)
        if version_id is not None:
            return df, version_id if version_id is None else df

    def upload_excel(self, file_path: str, bucket_name: str, object_name: str, version_id: str):
        """
        Uploads an Excel file to an S3 bucket and tags it with the raw data version ID.

        Args:
            file_path (str): The path to the Excel file.
            bucket_name (str): The name of the S3 bucket.
            object_name (str): The name of the object in S3.
            version_id (str): The version ID of the raw data to be used as a tag.
        """
        try:
            self.s3_client.upload_file(file_path, bucket_name, object_name)

            tagging = {"TagSet": [{"Key": "source_raw_version_id", "Value": version_id}]}
            self.s3_client.put_object_tagging(Bucket=bucket_name, Key=object_name, Tagging=tagging)

            logging.info(f"File {file_path} uploaded to {bucket_name}/{object_name} with tag source_raw_version_id={version_id}")
        except Exception as e:
            logging.error(f"Failed to upload file with tagging: {e}")
            raise
    

if __name__ == '__main__':
    data_management = DataManagement()
    path, version_id = data_management.load_s3_file("aimfiltech-bucket", "raw/231212_Lab data_2.xlsx")
    print(path)
    print("######")

    print(version_id)