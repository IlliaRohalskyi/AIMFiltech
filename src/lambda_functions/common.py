"""
Common utility functions for AWS Lambda handlers, including parameter validation.
"""


def check_missing_params(event, required_params):
    """
    Checks for missing parameters in the event dict and raises an exception if any are missing.

    Args:
        event (dict): The event dictionary.
        required_params (list): List of required parameter names.

    Returns:
        dict: extracted parameter values

    Raises:
        ValueError: if any required parameter is missing
    """
    missing_params = []
    extracted_params = {}
    for param in required_params:
        value = event.get(param)
        if not value:
            missing_params.append(param)
        extracted_params[param] = value

    if missing_params:
        error_msg = f"Missing required parameters: {', '.join(missing_params)}"
        raise ValueError(error_msg)

    return extracted_params
