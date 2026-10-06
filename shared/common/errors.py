from fastapi import HTTPException

class AppError(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

class ConflictError(AppError):
    def __init__(self, detail: str):
        super().__init__(status_code=409, detail=detail)

class NotFoundError(AppError):
    def __init__(self, detail: str):
        super().__init__(status_code=404, detail=detail)

class UnauthorizedError(AppError):
    def __init__(self, detail: str):
        super().__init__(status_code=401, detail=detail)

class ForbiddenError(AppError):
    def __init__(self, detail: str):
        super().__init__(status_code=403, detail=detail)

class GoneError(AppError):
    def __init__(self, detail: str):
        super().__init__(status_code=410, detail=detail)
