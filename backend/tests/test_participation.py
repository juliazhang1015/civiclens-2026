from datetime import date

import pytest

from app.analyzer import extract_dates, filter_historical_participation, verify_evidence
from app.schemas import DecisionAnalysis, Evidence, Finding, ParticipationStep


PAST_SURVEY = (
    "A participant questionnaire was distributed to past program participants and "
    "a public EngageWR survey was available online for 4 weeks through the "
    "City of Waterloo Engage page and promoted through social media."
)


def analysis_with_participation(quote: str) -> DecisionAnalysis:
    finding = ParticipationStep(text="Public consultation through EngageWR survey (4 weeks).", evidence=[
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


# --- A passed date must not hide a step that may still be open --------------

@pytest.mark.parametrize("quote", [
    "Report dated October 26, 2026. Written comments will be accepted until December 15.",   # no year
    "Notice issued October 1, 2026. Submit comments by 12/15/2026.",                           # numeric date
    "Notice of October 5, 2026: the survey is open November 1-30, 2026.",                      # day range
    "The online survey opened on November 1, 2026 and remains open.",                          # started, not ended
    "Since September 14, 2026, residents can submit comments to the Clerk at any time.",
])
def test_passed_date_beside_a_possibly_live_step_is_kept(quote):
    result = analysis_with_participation(quote)
    filter_historical_participation(result, today=TODAY)
    assert len(result.participation) == 1


def test_undated_second_quote_keeps_the_step():
    result = analysis_with_participation("Council Date: November 2, 2026")
    result.participation[0].evidence.append(
        Evidence(page=3, quote="A public meeting will be held on Monday, December 7 at 7 p.m. in Council Chambers."))
    filter_historical_participation(result, today=TODAY)
    assert len(result.participation) == 1


@pytest.mark.parametrize("text,expected", [
    ("the survey is open November 1-30, 2026", [date(2026, 11, 30)]),        # a range ends on its last day
    ("PUBLIC MEETING: JANUARY 15, 2024 AT 7 PM", [date(2024, 1, 15)]),
    ("Comments are welcome in May. 2025 saw record turnout.", []),           # sentence end, not "May 2025"
    ("held Sept. 9, 2025", [date(2025, 9, 9)]),
])
def test_extract_dates_edge_cases(text, expected):
    assert extract_dates(text) == expected


# --- The model states when each step ends; the PDF must back the date up --------

MEETING_QUOTE = "This meeting provides an opportunity to comment on the proposed changes within the updated plan."
DOCUMENT = ["Council Meeting          Page 1 of 2          December 1, 2025",
            MEETING_QUOTE + " Comments on the next phase close on March 1, 2027."]


def step(quote: str, ends_on: str | None) -> DecisionAnalysis:
    result = analysis_with_participation(quote)
    result.participation = [ParticipationStep(text="A chance to comment.", ends_on=ends_on,
                                              evidence=[Evidence(page=2, quote=quote)])]
    return result


def test_step_with_a_passed_end_date_is_removed_even_when_the_quote_has_no_date():
    # Seen live: the quote was undated and only the model's wording said "December 1, 2025".
    result = step(MEETING_QUOTE, "2025-12-01")
    filter_historical_participation(result, today=TODAY, pages=DOCUMENT)
    assert result.participation == []
    assert any("December 1, 2025 (page 2), which has passed" in note for note in result.unknowns)


def test_step_ending_in_the_future_is_kept_despite_past_wording():
    result = step("A survey was available online.", "2027-03-01")
    filter_historical_participation(result, today=TODAY, pages=DOCUMENT)
    assert len(result.participation) == 1


@pytest.mark.parametrize("ends_on", ["2024-06-30", "last spring", "2025-13-45", ""])
def test_end_date_the_pdf_does_not_contain_is_ignored(ends_on):
    # An invented or unreadable date must not remove a step; the quote rules decide instead.
    result = step("Residents can email comments to the City Clerk.", ends_on)
    filter_historical_participation(result, today=TODAY, pages=DOCUMENT)
    assert len(result.participation) == 1


def test_standing_channel_without_an_end_date_is_kept():
    result = step("Follow our project and provide feedback directly through engage.ca", None)
    filter_historical_participation(result, today=TODAY, pages=DOCUMENT)
    assert len(result.participation) == 1
