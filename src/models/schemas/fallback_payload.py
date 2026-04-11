from models.schemas.JobDetails import JobDetails


def fallback_payload() -> dict:
    return JobDetails(
        Job_Title="غير محدد",
        Company_Name=None,
        Location=None,
        Experience_Level="Not Specified",
        Min_Years_of_Experience=None,
        Max_Years_of_Experience=None,
        Salary=None,
        Tech_Stack=[],
        Work_Model="Not Specified",
        Core_Responsibilities=[],
    ).model_dump()
