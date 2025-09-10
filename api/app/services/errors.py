from __future__ import annotations


class ServiceError(Exception):
    """Base class for service-layer errors."""


class NotFoundError(ServiceError):
    pass


class ConflictError(ServiceError):
    pass


class ServiceValidationError(ServiceError):
    pass


class OperationError(ServiceError):
    pass


class BadRequestError(ServiceError):
    pass
