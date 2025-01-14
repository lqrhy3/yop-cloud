"""
settings.py

This module defines the config for the FastAPI application.
It contains configurations and settings used by the Django project. These include:

 - UPLOAD_DIR: The path to the uploaded files.
 - TMP_DIR: The path to the temporary directory.
 - LOGGER_CONFIG_PATH: The path to the logging configuration file.
 - ARCHIVE_HEADER: The name of the archive header.

"""

UPLOAD_DIR = '/uploaded_files'
TMP_DIR = '/tmp'
LOGGER_CONFIG_PATH = '/app/logger.json'
ARCHIVE_HEADER = 'X-Is-Archive'
