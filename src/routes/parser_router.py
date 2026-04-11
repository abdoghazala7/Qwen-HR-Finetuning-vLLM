from __future__ import annotations

import logging
from time import perf_counter

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from controller.parser_service import ParserService
from models.enums.ResponseSignals import ResponseSignals
from models.schemas.JobDetails import JobDetails
from models.schemas.fallback_payload import fallback_payload
from routes.schemas.job_description import JobDescriptionRequest

logger = logging.getLogger(__name__)

_FALLBACK_DATA = fallback_payload()

class JobDescriptionParseResponse(BaseModel):
    signal: ResponseSignals = Field(
        ..., description="Outcome signal for the parsing operation."
    )
    data: JobDetails = Field(..., description="Normalized parsed details from the JD text.")
    processing_time_ms: int = Field(
        ..., ge=0, description="Server-side processing time in milliseconds."
    )


parser_router = APIRouter(
    prefix="/api/v1/job-descriptions",
    tags=["Job Descriptions"],
)


@parser_router.post(
    path="/parse",
    response_model=JobDescriptionParseResponse,
    status_code=status.HTTP_200_OK,
    summary="Parse and structure a job description",
)
async def parse_job_description(
    payload: JobDescriptionRequest,
) -> JobDescriptionParseResponse:
    started_at = perf_counter()
    normalized_data = await ParserService.parse_job_description(payload.text)

    signal = (
        ResponseSignals.JOB_DESCRIPTION_PARSING_FALLBACK_USED
        if normalized_data.model_dump() == _FALLBACK_DATA
        else ResponseSignals.JOB_DESCRIPTION_PARSED_SUCCESSFULLY
    )

    duration_ms = max(int((perf_counter() - started_at) * 1000), 0)
    
    logger.info(f"Job Description parsed in {duration_ms} ms. Signal: {signal.name}")
    
    return JobDescriptionParseResponse(
        signal=signal,
        data=normalized_data,
        processing_time_ms=duration_ms,
    )


@parser_router.get(
    path="/schema",
    status_code=status.HTTP_200_OK,
    summary="Get target JSON schema used by the parser",
)
async def get_target_schema() -> dict:
    return JobDetails.model_json_schema()