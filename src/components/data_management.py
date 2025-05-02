"""
Data Management Module.

This module provides a class with methods for data management tasks.
"""

import os
import subprocess
from typing import Tuple

import boto3
import pandas as pd
import psycopg2
from sqlalchemy import create_engine

from src.errors.data_management_errors import (DeletionError,
                                               MultipleFilesError,
                                               PostgreSQLConnectionError,
                                               ReadingError,
                                               UnsupportedFileTypeError,
                                               WritingError)
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
        prefix = self.management_config["s3_prefix"]

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

    def get_sql_table(self, table_name) -> pd.DataFrame:
        """
        Retrieve data from a Postgres database table.

        This method triggers the retrieval of data from the database.

        Args:
            table_name (str): The name of the table

        Returns:
            pandas.DataFrame: A DataFrame containing the retrieved data.
        """
        hostname = os.environ.get("DB_HOSTNAME")
        database_name = os.environ.get("DB_NAME")
        username = os.environ.get("DB_USERNAME")
        password = os.environ.get("DB_PASSWORD")

        try:
            connection = psycopg2.connect(
                host=hostname, database=database_name, user=username, password=password
            )

        except PostgreSQLConnectionError as e:
            logging.error("Error connecting to PostgreSQL:", e)
            raise e
        query = f"SELECT * FROM {table_name};"

        try:
            data = pd.read_sql_query(query, connection)
        except ReadingError as e:
            logging.error("Error executing SQL query:", e)
            raise e

        if connection:
            connection.close()
        return data

    def write_data(self, data, table_name):
        """
        Write data to a table.

        Args:
            data (pd.DataFrame): A dataframe containing the data that is to be written
            table_name (str): The name of the table to write data to.
        """
        hostname = os.environ.get("DB_HOSTNAME")
        database_name = os.environ.get("DB_NAME")
        username = os.environ.get("DB_USERNAME")
        password = os.environ.get("DB_PASSWORD")
        try:
            engine = create_engine(
                f"postgresql://{username}:{password}@{hostname}/{database_name}"
            )
        except PostgreSQLConnectionError as e:
            logging.error("Error connecting to PostgreSQL:", e)
            raise e
        try:
            data.to_sql(table_name, engine, if_exists="append", index=False)
        except WritingError as e:
            logging.error("Error executing SQL query:", e)
            raise e

    def delete_data(self, table_name):
        """
        Delete data from a table.

        Args:
            table_name (str): The name of the table to be deleted
        """

        hostname = os.environ.get("DB_HOSTNAME")
        database_name = os.environ.get("DB_NAME")
        username = os.environ.get("DB_USERNAME")
        password = os.environ.get("DB_PASSWORD")

        try:
            connection = psycopg2.connect(
                host=hostname, database=database_name, user=username, password=password
            )

        except PostgreSQLConnectionError as e:
            logging.error("Error connecting to PostgreSQL:", e)
            raise e

        cursor = connection.cursor()

        delete_query = f"DELETE FROM {table_name}"
        try:
            cursor.execute(delete_query)
            connection.commit()
        except DeletionError as e:
            logging.error("Error executing SQL query:", e)
            raise e
        finally:
            cursor.close()
            connection.close()

    
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
    df = data_management.initiate_data_ingestion()