from typing import Annotated

from fastapi import Depends

from app.services import ArchiveService, FileService
from app.settings import Settings


def get_file_service(settings: Annotated[Settings, Depends(lambda: Settings())]):
    return FileService(settings)


def get_archive_service(settings: Annotated[Settings, Depends(lambda: Settings())]):
    return ArchiveService(settings)


SettingsDep = Annotated[Settings, Depends(lambda: Settings())]
FileServiceDep = Annotated[FileService, Depends(get_file_service)]
ArchiveServiceDep = Annotated[FileService, Depends(get_archive_service)]
