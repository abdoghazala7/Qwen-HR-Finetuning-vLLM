import re
from pydantic import BaseModel, Field, field_validator

MIN_WORDS = 30
_MIN_SIGNAL_MATCHES = 4

# ── Keywords that strongly indicate a real English job description 
_JOB_SIGNALS_PATTERN = re.compile(
    r"\b("
    r"job|position|role|vacancy|opening|opportunity|hiring|recruit"
    r"|engineer|developer|designer|analyst|manager|coordinator|specialist"
    r"|intern|director|lead|architect|consultant|officer|executive"
    r"|requirements|qualifications|responsibilities|duties|skills|experience"
    r"|proficient|familiar|knowledge|expertise|background|ability|capable"
    r"|bachelor|master|degree|diploma|certification|graduate|university|college"
    r"|remote|hybrid|on.site|full.time|part.time|contract|freelance|permanent"
    r"|team|department|company|organization|startup|agency|firm|employer"
    r"|salary|compensation|benefits|equity|bonus|package|insurance"
    r"|apply|submit|candidate|applicant|interview|resume|cv|portfolio"
    r")\b",
    re.IGNORECASE,
)

class JobDescriptionRequest(BaseModel):
    # Definition of the expected incoming payload, clearly forcing a valid string
    text: str = Field(
        ..., 
        min_length=50, 
        max_length=4000, 
        description="The full text of the job description"
    )

    @field_validator("text")
    @classmethod
    def validate_job_description(cls, value: str) -> str:
        value = value.strip()
        word_count = len(value.split())

        if word_count < MIN_WORDS:
            raise ValueError(
                f"A valid job description requires at least {MIN_WORDS} words."
            )

        unique_matches = {m.lower() for m in _JOB_SIGNALS_PATTERN.findall(value)}
        if len(unique_matches) < _MIN_SIGNAL_MATCHES:
            raise ValueError("The provided text does not appear to be a real job description.")

        return value
