import pytest
from pydantic import ValidationError

from app.analyzer import verify_evidence
from app.schemas import DecisionAnalysis, Evidence, Finding, KeyFact

PAGE = "The project budget is $2.4 million. Comments are due January 15, 2027."


def fact(kind: str, value: str, quote: str, page: int = 1) -> KeyFact:
    return KeyFact(kind=kind, label="A label", value=value, evidence=[Evidence(page=page, quote=quote)])


def analysis(*facts: KeyFact) -> DecisionAnalysis:
    return analysis_with_summary("The project budget is $2.4 million", *facts)


def analysis_with_summary(summary_quote: str, *facts: KeyFact) -> DecisionAnalysis:
    summary = Finding(text="Summary.", evidence=[Evidence(page=1, quote=summary_quote)])
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


@pytest.mark.parametrize("value,quote", [
    ("$500", "The grant is $500,000"),
    ("$12", "total project budget is $12.4 million"),
    ("2.4 million", "total project budget is $12.4 million"),
    ("$12.4", "total project budget is $12.4 million"),          # the unit is part of the amount
    ("March 1", "Comments are due March 15, 2027"),
    ("5, 2027", "Comments are due March 15, 2027"),
    ("1", "The fee rises from $1,250 to $1,400 per unit"),
    ("40", "a 40% increase in fees"),
])
def test_value_must_be_the_whole_figure(value, quote):
    result = analysis_with_summary(quote, fact("amount", value, quote))
    verify_evidence(result, [quote])
    assert result.key_facts == []


@pytest.mark.parametrize("value,quote", [
    ("$500,000.", "The grant is $500,000."),                     # stray sentence punctuation
    ("$12.4 million", "total project budget is $12.4 million, including design"),
    ("March 15, 2027", "Comments are due March 15, 2027"),
    ("40%", "a 40% increase in fees"),
    ("$1,250", "The fee rises from $1,250 to $1,400 per unit"),
])
def test_whole_figures_pass(value, quote):
    result = analysis_with_summary(quote, fact("amount", value, quote))
    verify_evidence(result, [quote])
    assert len(result.key_facts) == 1
