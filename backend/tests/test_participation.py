from datetime import date

import pytest

from app.analyzer import extract_dates, filter_historical_participation, verify_evidence
from app.schemas import DecisionAnalysis, Evidence, Finding


PAST_SURVEY = (
    "A participant questionnaire was distributed to past program participants and "
    "a public EngageWR survey was available online for 4 weeks through the "
    "City of Waterloo Engage page and promoted through social media."
)


def analysis_with_participation(quote: str) -> DecisionAnalysis:
    finding = Finding(text="Public consultation through EngageWR survey (4 weeks).", evidence=[
        Evidence(page=2, quote=quote)
    ])
    return DecisionAnalysis(
        document_title="CIP update",
        summary=Finding(text="The report discusses consultation.", evidence=[
            Evidence(page=2, quote=quote)
        ]),
        key_facts=[],
        proposed_changes=[],
        affected_groups=[],
        potential_benefits=[],
        potential_tradeoffs=[],
        participation=[finding],
        unknowns=[],
    )


def test_historical_engagewr_survey_not_presented_as_next_step():
    result = analysis_with_participation(PAST_SURVEY)
    verify_evidence(result, ["Other page", PAST_SURVEY])
    filter_historical_participation(result)
    assert result.participation == []
    assert any("past consultation" in item for item in result.unknowns)
    assert result.summary.text == "The report discusses consultation."


def test_upcoming_public_meeting_stays_in_participation():
    quote = "The public meeting will be held on December 1, 2025."
    result = analysis_with_participation(quote)
    # Pinned to a day before the meeting: the result now depends on the date.
    filter_historical_participation(result, today=date(2025, 11, 1))
    assert len(result.participation) == 1


def test_mixed_evidence_is_retained_for_human_review():
    quote = "The previous survey was available online, and a new meeting will be held in December."
    result = analysis_with_participation(quote)
    filter_historical_participation(result)
    assert len(result.participation) == 1


# --- Dates decide before wording does -------------------------------------


TODAY = date(2026, 11, 14)


@pytest.mark.parametrize("text,expected", [
    ("Council Date: December 1, 2025", [date(2025, 12, 1)]),
    ("on Dec. 1st, 2025 at 6 p.m.", [date(2025, 12, 1)]),
    ("held 3 March 2022 and 14 June 2023", [date(2022, 3, 3), date(2023, 6, 14)]),
    ("comments accepted until 2027-01-15", [date(2027, 1, 15)]),
    ("a decision is expected in March 2027", [date(2027, 3, 31)]),   # month only: its last day
    ("Thursday, March 3 at City Hall", []),                          # no year, no guess
    ("February 30, 2025 and report COM2025-032", []),                # impossible date, report number
    ("May 2025 survey; staff may 2026 respond", [date(2025, 5, 31)]),  # "may" the verb
])
def test_extract_dates(text, expected):
    assert extract_dates(text) == expected


@pytest.mark.parametrize("quote", [
    "A public information centre on March 3, 2022 at 6 p.m. at City Hall.",
    "Public Information Centre #1 – June 14, 2023",
    "The statutory public meeting was scheduled for May 9, 2022.",
    "Residents can submit comments by January 15, 2026.",
    "Council will consider the report on December 1, 2025.",
])
def test_dated_past_event_is_not_a_next_step(quote):
    result = analysis_with_participation(quote)
    filter_historical_participation(result, today=TODAY)
    assert result.participation == []
    assert any("has passed" in note and "page 2" in note for note in result.unknowns)


def test_note_names_the_passed_date():
    result = analysis_with_participation("Residents can submit comments by January 15, 2026.")
    filter_historical_participation(result, today=TODAY)
    assert any("January 15, 2026" in note for note in result.unknowns)


@pytest.mark.parametrize("quote", [
    "Residents can submit comments by January 15, 2027.",
    "The survey was open in May 2025; a second public meeting will be held on December 3, 2026.",
    "A public meeting is scheduled for November 14, 2026.",          # today still counts
])
def test_upcoming_date_keeps_the_next_step(quote):
    result = analysis_with_participation(quote)
    filter_historical_participation(result, today=TODAY)
    assert len(result.participation) == 1
    assert not any("has passed" in note for note in result.unknowns)


def test_past_wording_with_a_future_date_is_kept():
    # "was held" alone used to remove this; the future date now decides.
    result = analysis_with_participation("An open house was held in 2025. Comments close on March 1, 2027.")
    filter_historical_participation(result, today=TODAY)
    assert len(result.participation) == 1


def test_undated_quotes_fall_back_to_wording():
    result = analysis_with_participation(PAST_SURVEY)
    filter_historical_participation(result, today=TODAY)
    assert result.participation == []
    kept = analysis_with_participation("Delegations may register with the City Clerk.")
    filter_historical_participation(kept, today=TODAY)
    assert len(kept.participation) == 1
