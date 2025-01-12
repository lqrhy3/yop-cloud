from fastapi import HTTPException, status
from fastapi.responses import JSONResponse


Unauthorized = JSONResponse(content={"detail": "Not authenticated"}, status_code=status.HTTP_401_UNAUTHORIZED)
FileNotFound = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
