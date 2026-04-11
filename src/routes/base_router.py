from __future__ import annotations

from typing import Literal
from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from core.config import get_config
from models.enums.ResponseSignals import ResponseSignals


class HealthCheckResponse(BaseModel):
    project_name: str = Field(..., description="Configured application name.")
    status: Literal["ok"] = Field("ok", description="Liveness state of the API.")
    signal: ResponseSignals = Field(
        ..., description="Structured response signal from the API domain."
    )


settings = get_config()

base_router = APIRouter(
    prefix="/api/v1",
    tags=["Health Check"],
)


@base_router.get(
    path="/",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="API health and welcome endpoint",
)
async def health_check() -> HealthCheckResponse:
    return HealthCheckResponse(
        project_name=settings.PROJECT_NAME,
        signal=ResponseSignals.WELCOME_AND_HEALTH_CHECK_MESSAGE
        )