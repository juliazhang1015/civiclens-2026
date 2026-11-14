import pytest
from pydantic import ValidationError

from app.analyzer import verify_evidence
from app.schemas import DecisionAnalysis, Evidence, Finding, KeyFact

PAGE = "The project budget is $2.4 million. Comments are due January 15, 2027."


def fact(kind: str, value: str, quote: str, page: int = 1) -> KeyFact:
    return KeyFact(kind=kind, label="A label", value=value, evidence=[Evidence(page=page, quote=quote)])


def analysis(*facts: KeyFact) -> DecisionAnalysis:
    summary = Finding(text="Summary.", evidence=[Evidence(page=1, quote="The project budget is $2.4 million")])
    return DecisionAnalysis(document_title="Test", summary=summary, key_facts=list(facts), proposed_changes=[],
                            affected_groups=[], potential_benefits=[], potential_tradeoffs=[], participation=[],
                            unknowns=[])


def test_supported_facts_are_kept():
    amount = fact("amount", "$2.4 million", "project budget is $2.4 million")
    deadline = fact("date", "January 15, 2027", "Comments are due January 15, 2027")
    result = analysis(amount, deadline)
    verify_evidence(result, [PAGE])
    assert result.key_facts == [amount, deadline]


@pytest.mark.parametrize("value,quote", [
    ("$24 million", "project budget is $2.4 million"),        # value is not what the quote says
    ("$2.4 million", "The project budget is $9.9 million"),   # quote is not in the PDF
    ("January 15, 2028", "Comments are due January 15, 2027"),
    ("The project budget", "The project budget is $2.4 million"),  # not an amount or a date: no digit
])
def test_fact_is_dropped_when_value_or_quote_is_unsupported(value, quote):
    result = analysis(fact("amount", value, quote))
    verify_evidence(result, [PAGE])
    assert result.key_facts == []


def test_value_match_ignores_case_and_typography():
    result = analysis(fact("date", "january 15, 2027", "Comments are due January 15, 2027"))
    verify_evidence(result, [PAGE])
    assert len(result.key_facts) == 1


def test_dropped_facts_do_not_reject_the_analysis_or_count_as_statements():
    result = analysis(fact("amount", "$1", "invented"))
    assert verify_evidence(result, [PAGE]) == 0
    assert result.unknowns == []


def test_kind_is_restricted():
    with pytest.raises(ValidationError):
        fact("opinion", "$2.4 million", "project budget is $2.4 million")
