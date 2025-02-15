from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    STORAGE_DATA_PATH: str = "/storage_data"
    TEMP_DATA_PATH: str = "/storage_data/.tmp"

    DISK_USAGE_OFFSET: int = 1 * 1024 * 1024 * 1024  # 5GB

    MAX_FILE_NAME_LENGTH: int = 256

    IS_ARCHIVE_HEADER: str = "X-Is-Archive"

    ARCHIVE_EXTENSION: str = ".tar.gz"

    LOGGER_CONFIG_PATH: str = "/app/logger.json"

    # class Config:
    #     env_file = ".env"
