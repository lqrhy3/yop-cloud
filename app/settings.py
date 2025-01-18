"""
settings.py

This module defines the config for the FastAPI application.
It contains configurations and settings used by the Django project. These include:

 - UPLOAD_DIR: The path to the uploaded files.
 - TMP_DIR: The path to the temporary directory.
 - LOGGER_CONFIG_PATH: The path to the logging configuration file.
 - ARCHIVE_HEADER: The name of the archive header.
 - ARCHIVE_EXTENSION: Extension of the archive file.
 - ZIP_COMMAND: Command to compress the archive file.
 - UNZIP_COMMAND: Command to uncompress the archive file.

"""

UPLOAD_DIR = '/storage'
TMP_DIR = '/tmp/storage'
LOGGER_CONFIG_PATH = '/app/logger.json'
ARCHIVE_HEADER = 'X-Is-Archive'
ARCHIVE_EXTENSION = '.tar.gz'
ZIP_COMMAND = ''
UNZIP_COMMAND = ''
