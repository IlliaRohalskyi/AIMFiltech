"""
Logging Module.

Provides logging setup with timestamped log entries for traceability.
Logs output to the console, suitable for AWS Lambda and Docker environments.

Example:
    from src.logger import logging

    if __name__ == '__main__':
        logging.info("Logging has started")
"""

import logging

logging.basicConfig(
    format="[ %(asctime)s ] %(lineno)d %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
