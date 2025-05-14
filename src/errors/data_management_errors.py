"""
This module contains all the errors for data_management.py module
"""


class VersioningError(Exception):
    """
    Error that is raised when the versioning of the file is not enabled.
    """

    def __init__(self, bucket_name):
        super().__init__(
            f"Versioning is not enabled for the bucket: {bucket_name}. "
            "Please enable versioning to proceed."
        )
