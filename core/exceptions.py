class BaseException(Exception):
    pass

class ConfigurationError(BaseException):
    pass

class APIError(BaseException):
    pass

class DatabaseError(BaseException):
    pass

class ValidationError(BaseException):
    pass

class WorkflowError(BaseException):
    pass

class KnowledgeGraphError(BaseException):
    pass

class VectorDBError(BaseException):
    pass
