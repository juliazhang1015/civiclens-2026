from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Evidence(StrictModel):
    page: int = Field(ge=1)
    quote: str = Field(min_length=1)


class Finding(StrictModel):
    text: str = Field(min_length=1)
    evidence: list[Evidence] = Field(min_length=1)


class KeyFact(StrictModel):
    """An amount or date residents should not miss; `value` is copied from the quote."""
    kind: Literal["amount", "date"]
    label: str = Field(min_length=1)
    value: str = Field(min_length=1)
    evidence: list[Evidence] = Field(min_length=1)


class DecisionAnalysis(StrictModel):
    document_title: str = Field(min_length=1)
    summary: Finding
    key_facts: list[KeyFact]
    proposed_changes: list[Finding]
    affected_groups: list[Finding]
    potential_benefits: list[Finding]
    potential_tradeoffs: list[Finding]
    participation: list[Finding]
    unknowns: list[str]
