from pydantic import BaseModel, Field
from typing import Optional, List, Literal

ExperienceLevel = Literal["Junior", "Mid-level", "Senior", "Executive", "Not Specified"]
WorkModel = Literal["Remote", "On-site", "Hybrid", "Not Specified"]
class JobDetails(BaseModel):
    Job_Title: str = Field(..., description="The Arabic translation of the exact job title.")
    Company_Name: Optional[str] = Field(None, description="The company name, or null if strictly confidential or not mentioned.")
    Location: Optional[str] = Field(None, description="The Arabic translation of the location (e.g., 'القاهرة', 'عن بعد'), or null if not mentioned.")
    Experience_Level: ExperienceLevel = Field(..., description="Select strictly ONE option that matches the required experience level.")
    Min_Years_of_Experience: Optional[int] = Field(None, description="The MINIMUM number of years of experience required as an integer (e.g., 3), or null.")
    Max_Years_of_Experience: Optional[int] = Field(None, description="The MAXIMUM number of years of experience required as an integer (e.g., 5), or null.")
    Salary: Optional[str] = Field(None, description="The mentioned salary range or compensation translated to Arabic if needed, or null if not mentioned.")
    Tech_Stack: List[str] = Field(..., description="List of technical skills and tools ONLY, kept strictly in English. If none mentioned, return an empty list [].")
    Work_Model: WorkModel = Field(..., description="Select strictly ONE work model.")
    Core_Responsibilities: List[str] = Field(..., description="Extract 1-5 main responsibilities and translate them into professional Arabic.")