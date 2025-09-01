from pydantic import BaseModel


class WelcomeResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str
    message: str


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: list[ErrorDetail] | None = None
    timestamp: str
    request_id: str
