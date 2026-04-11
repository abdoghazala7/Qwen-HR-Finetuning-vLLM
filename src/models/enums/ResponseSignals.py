from enum import Enum


class ResponseSignals(str, Enum):
    WELCOME_AND_HEALTH_CHECK_MESSAGE = "Welcome to the API! The service is up and running ✅"
    JOB_DESCRIPTION_PARSED_SUCCESSFULLY = "Job description parsed successfully ✅"
    JOB_DESCRIPTION_PARSING_FALLBACK_USED = "Model response was invalid; fallback payload returned ⚠️"
