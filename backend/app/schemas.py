from pydantic import BaseModel, Field


class Evidence(BaseModel):
    page: int = Field(ge=1)
    quote: str


class Finding(BaseModel):
    text: str
    evidence: list[Evidence] = Field(default_factory=list)


class DecisionAnalysis(BaseModel):
    document_title: str
    summary: Finding
    proposed_changes: list[Finding] = Field(default_factory=list)
    affected_groups: list[Finding] = Field(default_factory=list)
    potential_benefits: list[Finding] = Field(default_factory=list)
    potential_tradeoffs: list[Finding] = Field(default_factory=list)
    participation: list[Finding] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
