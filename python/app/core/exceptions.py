from typing import Any

class TinfoilException(Exception):
    def __init__(self, message: str, details: Any = None):
        self.message = message
        self.details = details
        super().__init__(self.message)

class ProcessingError(TinfoilException):
    pass

class CogError(TinfoilException):
    pass

class FileNotFoundError(TinfoilException):
    pass

class ValidationError(TinfoilException):
    pass

class ConfigurationError(TinfoilException):
    pass