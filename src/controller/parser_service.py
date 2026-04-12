import json
import logging

import httpx
from fastapi import HTTPException
from pydantic import ValidationError

from controller.output_cleaning import OutputCleaning
from core.config import get_config
from utils.metrics import (
    classify_vllm_error,
    observe_parser_duration,
    observe_vllm_duration,
    record_fallback,
    record_job_description_size,
    record_vllm_error,
)
from models.enums.SystemPrompt import SYSTEM_PROMPT
from models.schemas.JobDetails import JobDetails
from models.schemas.fallback_payload import fallback_payload

settings = get_config()
logger = logging.getLogger(__name__)

class ParserService:
    @staticmethod
    async def parse_job_description(job_description: str) -> JobDetails:
        if not job_description or not job_description.strip():
            raise HTTPException(status_code=400, detail="job_description cannot be empty.")

        record_job_description_size(job_description)

        # Ensure no trailing slash causes double slashes in the URL
        base_url = settings.VLLM_NGROK_URL.rstrip("/")
        url = f"{base_url}/v1/chat/completions"

        headers = {"Content-Type": "application/json"}
        json_schema = JobDetails.model_json_schema()

        payload = {
            "model": "jobs_lora",
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": f"Extract information from:\n\n{job_description}"
                }
            ],
            "temperature": 0.0,
            "max_tokens": 1024,
            "stop": ["<|im_end|>", "<|endoftext|>"],
            "guided_json": json_schema
        }

        raw_content = ""

        with observe_parser_duration() as parser_state:
            try:
                with observe_vllm_duration(model="jobs_lora") as vllm_state:
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        response = await client.post(url, json=payload, headers=headers)
                        response.raise_for_status()
                        data = response.json()
                    vllm_state["outcome"] = "success"

                choices = data.get("choices") or []
                if not choices:
                    logger.warning("AI parser returned no choices. Returning fallback JSON.")
                    record_fallback(reason="no_choices")
                    parser_state["outcome"] = "fallback"
                    return JobDetails.model_validate(fallback_payload())

                raw_content = choices[0].get("message", {}).get("content", "")
                if not raw_content:
                    logger.warning("AI parser returned empty content. Returning fallback JSON.")
                    record_fallback(reason="empty_content")
                    parser_state["outcome"] = "fallback"
                    return JobDetails.model_validate(fallback_payload())

                clean_content = OutputCleaning.clean_output(raw_content)
                parsed_content = json.loads(clean_content)
                validated_payload = JobDetails.model_validate(parsed_content)

                parser_state["outcome"] = "success"
                return validated_payload

            except httpx.RequestError as exc:
                error_type, status_class = classify_vllm_error(exc)
                record_vllm_error(model="jobs_lora", error_type=error_type, status_class=status_class)
                parser_state["outcome"] = "vllm_error"
                logger.exception("AI engine request failed.")
                raise HTTPException(status_code=503, detail=f"AI Engine is unavailable: {str(exc)}") from exc

            except httpx.HTTPStatusError as exc:
                error_type, status_class = classify_vllm_error(exc)
                record_vllm_error(model="jobs_lora", error_type=error_type, status_class=status_class)
                parser_state["outcome"] = "vllm_error"
                logger.exception("AI engine returned an HTTP error.")
                raise HTTPException(
                    status_code=exc.response.status_code,
                    detail=f"Error from AI Engine: {exc.response.text}",
                ) from exc

            except (json.JSONDecodeError, ValidationError) as exc:
                logger.warning(
                    "Model response was not valid schema JSON. Returning fallback. reason=%s raw_preview=%s",
                    str(exc),
                    raw_content[:300],
                )
                record_fallback(reason="invalid_schema_response")
                parser_state["outcome"] = "fallback"
                return JobDetails.model_validate(fallback_payload())