from pydantic import BaseModel, Field


class CompanyName(BaseModel):
    """Company scheme.

    Attributes:
        company_name: str
    """

    company_name: str = Field(max_length=120)
