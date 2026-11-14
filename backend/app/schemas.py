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


class ParticipationStep(Finding):
    """A way to take part. `ends_on` is the day it takes place or closes, as YYYY-MM-DD,
    when the document gives one; null for a standing channel with no end date."""
    ends_on: str | None = None


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
    participation: list[ParticipationStep]
    unknowns: list[str]


class MergedSelection(StrictModel):
    """What the model returns when combining the parts of a long document: ids of
    statements already checked against the PDF, plus one newly written summary."""
    summary: str
    summary_sources: list[int]
    key_facts: list[int]
    proposed_changes: list[int]
    affected_groups: list[int]
    potential_benefits: list[int]
    potential_tradeoffs: list[int]
    participation: list[int]
    unknowns: list[str]
