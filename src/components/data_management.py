"""
Data Management Module.

This module provides a class with methods for data management tasks.
"""

import os
from typing import Optional, Tuple

import boto3
import pandas as pd

from src.errors.data_management_errors import VersioningError
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

    def load_s3_file(
        self, bucket: str, key: str, version_id: Optional[str] = None
    ) -> Tuple[pd.DataFrame, str]:
        """
        Loads a file from S3, optionally with a version_id.
        If version_id is not provided, fetches the latest version.

        Args:
            bucket (str): The name of the S3 bucket.
            key (str): The S3 object key.
            version_id (str, optional): The version ID of the S3 object. Defaults to None.

        Returns:
            tuple: (DataFrame with the loaded data, version_id of the file)

        Raises:
            FileNotFoundError: If the file or version information cannot be found
            VersioningError: If versioning issues occur
        """
        if not os.path.exists("/tmp"):
            os.makedirs("/tmp")
        local_file_path = os.path.join("/tmp", os.path.basename(key))

        if version_id is None:
            version_response = self.s3_client.list_object_versions(
                Bucket=bucket, Prefix=key
            )
            if "Versions" not in version_response:
                raise VersioningError("No versioning information available for file")
            latest_version = next(
                (v for v in version_response["Versions"] if v["Key"] == key), None
            )
            if not latest_version:
                raise FileNotFoundError("Unable to fetch latest version for file")
            version_id = latest_version["VersionId"]

        self.s3_client.download_file(
            bucket, key, local_file_path, ExtraArgs={"VersionId": version_id}
        )

        if key.endswith(".csv"):
            df = pd.read_csv(local_file_path)
        else:
            df = pd.read_excel(local_file_path)

        return df, version_id

    def upload_excel(
        self, file_path: str, bucket_name: str, object_name: str, version_id: str
    ) -> None:
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

            tagging = {
                "TagSet": [{"Key": "source_raw_version_id", "Value": version_id}]
            }
            self.s3_client.put_object_tagging(
                Bucket=bucket_name, Key=object_name, Tagging=tagging
            )

            logging.info(
                f"File {file_path} uploaded to {bucket_name}/{object_name} "
                f"with tag source_raw_version_id={version_id}"
            )
        except Exception as e:
            logging.error(f"Failed to upload file with tagging: {e}")
            raise
