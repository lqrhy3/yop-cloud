from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    STORAGE_DATA_PATH: str = "/storage_data"
    TMP_DATA_PATH: str = "/tmp"

    MAX_FILE_NAME_LENGTH: int = 256

    ARCHIVE_HEADER: str = "X-Is-Archive"

    ARCHIVE_EXTENSION: str = ".tar.gz"

    LOGGER_CONFIG_PATH: str = "/app/logger.json"

    # class Config:
    #     env_file = ".env"
