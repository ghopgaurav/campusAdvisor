from pydantic import BaseModel


class StudentProfile(BaseModel):
    """Optional student profile sent with each message for personalization."""

    gpa: float | None = None
    gpa_scale: float = 4.0
    undergrad_institution: str | None = None
    undergrad_country: str | None = None
    major: str | None = None
    degree_target: str | None = None          # "MS", "PhD", "MBA"
    field_target: str | None = None           # "Computer Science", etc.
    gre_quant: int | None = None
    gre_verbal: int | None = None
    gmat_score: int | None = None
    toefl_score: int | None = None
    ielts_score: float | None = None
    work_experience_years: float | None = None
    research_papers: int | None = None
    budget_total_usd: int | None = None
    needs_funding: bool = False
    preferences: dict | None = None           # e.g. {"climate": "warm", "city_size": "large"}


class ChatMessage(BaseModel):
    role: str   # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: list[ChatMessage] = []
    student_profile: StudentProfile | None = None


class ToolUsageInfo(BaseModel):
    tool_name: str
    query: str | None = None
    source_url: str | None = None


class ChatResponse(BaseModel):
    response: str
    tools_used: list[ToolUsageInfo] = []
    follow_up_suggestions: list[str] = []
