from fastapi import HTTPException


class CustomException(HTTPException):
    def __init__(self, status_code: int, message: str, error_code: str | None = None):
        self.message = message
        self.error_code = error_code
        super().__init__(status_code=status_code, detail=message)


class NotFoundException(CustomException):
    def __init__(self, message: str = "Recurso no encontrado"):
        super().__init__(status_code=404, message=message, error_code="NOT_FOUND")


class AuthorizationException(CustomException):
    def __init__(self, message: str = "No tienes permisos para esta accion"):
        super().__init__(status_code=403, message=message, error_code="FORBIDDEN")


class ValidationException(CustomException):
    def __init__(self, message: str = "Datos invalidos"):
        super().__init__(status_code=422, message=message, error_code="VALIDATION_ERROR")


class AuthenticationException(CustomException):
    def __init__(self, message: str = "Credenciales invalidas"):
        super().__init__(status_code=401, message=message, error_code="UNAUTHENTICATED")
