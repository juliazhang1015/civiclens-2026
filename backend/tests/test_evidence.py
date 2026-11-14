import pytest

from app.analyzer import verify_evidence
from app.schemas import DecisionAnalysis, Evidence, Finding

PAGE = "A protected cycle lane is proposed on King Street."
SUMMARY_QUOTE = "A protected cycle lane is proposed"


def finding(text: str, *quotes: tuple[int, str]) -> Finding:
    return Finding(text=text, evidence=[Evidence(page=page, quote=quote) for page, quote in quotes])


def analysis(summary_quote: str = SUMMARY_QUOTE, **categories: list[Finding]) -> DecisionAnalysis:
    fields = {name: [] for name in ("proposed_changes", "affected_groups", "potential_benefits",
                                    "potential_tradeoffs", "participation")}
    fields.update(categories)
    return DecisionAnalysis(document_title="Test", summary=finding("Summary.", (1, summary_quote)),
                            key_facts=[], unknowns=[], **fields)


@pytest.mark.parametrize("model_quote,pdf_text", [
    ("the City's plan", "the City’s plan"),                  # curly apostrophe
    ('"complete streets"', "“complete streets”"),       # curly double quotes
    ("the 2024-2027 budget", "the 2024–2027 budget"),        # en dash
    ("costs - if approved - rise", "costs — if approved — rise"),  # em dash
    ("the development will", "the develop-\nment will"),          # line-break hyphenation
    ("a long-term lease", "a long-\nterm lease"),                 # real hyphen at a line break
    ("cooperation agreement", "co­operation agreement"),     # soft hyphen
    ("the development will", "the develop­\nment will"),     # soft hyphen at a line break
    ("long-term development", "a long-\nterm develop-\nment plan"),  # both kinds on one page
    ("develop- ment will", "the develop-\nment will"),            # model copied the line break
    ("the 2024-2027 budget", "the 2024-\n2027 budget"),           # number range across lines
    ("costs — if approved — rise", "costs —\nif approved — rise"),  # spaced dash at a line end
    ("increase of 5 - 10 percent", "increase of 5 -\n10 percent"),
    ("items: - parking - transit", "items:\n- parking -\n transit"),  # bullet dashes
    # The model copies the source line break itself, as a newline or as a space.
    ("pages 1-\n5 of the plan", "pages 1-\n5 of the plan"),
    ("pages 1- 5 of the plan", "pages 1-\n5 of the plan"),
    ("the develop-\nment will", "the develop-\nment will"),
    ("the develop­\nment will", "the develop­\nment will"),
    ("the develop­ ment will", "the develop­\nment will"),
    ("seek to enter into a new lease agreement...","seek to enter into a new lease agreement, under"),  # model marks a cut
    ("… a new lease agreement …", "seek to enter into a new lease agreement, under"),
])
def test_typographic_variants_still_match(model_quote, pdf_text):
    result = analysis(summary_quote=model_quote)
    assert verify_evidence(result, [pdf_text]) == 0


@pytest.mark.parametrize("model_quote,pdf_text", [
    ("pages 15 of the plan", "pages 1-5 of the plan"),            # hyphens are not simply deleted
    ("pages 15 of the plan", "pages 1-\n5 of the plan"),          # ...nor across a line break
    ("a reduction of 3050 units", "a reduction of 30–\n50 units"),
    ("fee rises to $1500", "fee rises to $1-\n500"),
    ("the budget is $2.5 million", "the budget is $25 million"),  # punctuation in numbers matters
    ("Council approved the plan", "Council has not approved the plan"),
    ("Council ... approved the plan", "Council has not approved the plan"),  # no skipping words mid-quote
    ("...", "Any page text."),
])
def test_different_wording_or_numbers_do_not_match(model_quote, pdf_text):
    with pytest.raises(ValueError):
        verify_evidence(analysis(summary_quote=model_quote), [pdf_text])


def test_unmatched_finding_is_dropped_and_the_rest_kept():
    good = finding("A cycle lane is proposed.", (1, "cycle lane is proposed on King Street"))
    invented = finding("Parking fees will double.", (1, "Parking fees will double"))
    result = analysis(proposed_changes=[good, invented])

    assert verify_evidence(result, [PAGE]) == 1
    assert result.proposed_changes == [good]
    assert any("1 AI-generated statement" in note for note in result.unknowns)


@pytest.mark.parametrize("bad_quote", [(1, "Parking fees will double"), (9, "protected cycle lane")])
def test_finding_with_any_unmatched_quote_is_dropped(bad_quote):
    # One matching quote must not carry the unsupported half of a statement.
    partly = finding("A cycle lane is proposed and parking fees will double.", (1, "protected cycle lane"), bad_quote)
    result = analysis(proposed_changes=[partly])

    assert verify_evidence(result, [PAGE]) == 1
    assert result.proposed_changes == []
    assert any("1 AI-generated statement" in note for note in result.unknowns)


def test_unsupported_summary_still_rejects_the_whole_analysis():
    with pytest.raises(ValueError):
        verify_evidence(analysis(summary_quote="Invented summary quote"), [PAGE])


def test_partly_supported_summary_rejects_the_whole_analysis():
    result = analysis()
    result.summary = finding("A cycle lane is proposed and parking fees will double.",
                             (1, SUMMARY_QUOTE), (1, "Parking fees will double"))
    with pytest.raises(ValueError):
        verify_evidence(result, [PAGE])
