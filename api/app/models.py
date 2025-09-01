from pydantic import BaseModel


class WelcomeResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str
    message: str