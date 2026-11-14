from app.analyzer import filter_historical_participation, verify_evidence
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
    filter_historical_participation(result)
    assert len(result.participation) == 1


def test_mixed_evidence_is_retained_for_human_review():
    quote = "The previous survey was available online, and a new meeting will be held in December."
    result = analysis_with_participation(quote)
    filter_historical_participation(result)
    assert len(result.participation) == 1
