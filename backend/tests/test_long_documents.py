import asyncio
import re
import sys

import pytest

from app import analyzer
from app.analyzer import InputSizeError, chunk_pages
from app.schemas import DecisionAnalysis, MergedSelection

PAGES = [
    "Staff report on King Street. Council Date: March 1, 2027.",
    "A protected cycle lane is proposed on King Street.",
    "",
    "The estimated construction cost is $2.4 million.",
    "Forty parking spaces would be removed near the market.",
]


def test_chunks_keep_whole_pages_in_order_and_skip_blank_ones():
    assert chunk_pages(["a" * 40, "b" * 40, "", "c" * 40, "d" * 10], budget=90) == [[1, 2], [4, 5]]
    assert chunk_pages(["a" * 40, "b" * 40], budget=1000) == [[1, 2]]


def test_a_page_larger_than_the_budget_is_rejected_not_cut():
    with pytest.raises(InputSizeError, match="Page 2 .*too much text"):
        chunk_pages(["short", "x" * 101], budget=100)


def finding(text: str, page: int, quote: str) -> dict:
    return {"text": text, "evidence": [{"page": page, "quote": quote}]}


def part_analysis(page_numbers: list[int]) -> DecisionAnalysis:
    """A stand-in model: one statement per page, quoting that page's own text."""
    own = [n for n in page_numbers if PAGES[n - 1]]
    statements = [finding(f"Statement about page {n}.", n, PAGES[n - 1]) for n in own]
    facts = [{"kind": "amount", "label": "Construction cost", "value": "$2.4 million",
              "evidence": [{"page": 4, "quote": PAGES[3]}]}] if 4 in own else []
    return DecisionAnalysis(document_title=f"Part with page {own[0]}", summary=statements[0], key_facts=facts,
                            proposed_changes=statements, affected_groups=[], potential_benefits=[],
                            potential_tradeoffs=[], participation=[], unknowns=[f"Question from page {own[0]}?"])


def candidate_ids(prompt: str) -> dict[str, list[int]]:
    ids, section = {}, None
    for line in prompt.splitlines():
        if re.fullmatch(r"[A-Z_ ]+", line):
            section = line
        elif match := re.match(r"\[(\d+)\]", line):
            ids.setdefault(section, []).append(int(match.group(1)))
    return ids


class FakeModel:
    def __init__(self, merge=None, fail_part=None, part_error=ValueError("bad JSON")):
        self.calls, self.merge, self.fail_part, self.part_error = [], merge, fail_part, part_error

    async def __call__(self, system, user, schema):
        self.calls.append((schema, user))
        if schema is DecisionAnalysis:
            # The repeated page-1 context is labelled; the part's own pages are not.
            own = [int(n) for n in re.findall(r"^\[PDF PAGE (\d+)\]$", user, re.M)]
            if self.fail_part and self.fail_part in own:
                raise self.part_error
            return part_analysis(own)
        if isinstance(self.merge, Exception):
            raise self.merge
        ids = candidate_ids(user)
        return self.merge(ids) if self.merge else MergedSelection(
            summary="A cycle lane is proposed for $2.4 million.",
            summary_sources=ids.get("KEY_FACTS", []) + ids["PROPOSED_CHANGES"][:1],
            key_facts=ids.get("KEY_FACTS", []), proposed_changes=ids["PROPOSED_CHANGES"], affected_groups=[], potential_benefits=[],
            potential_tradeoffs=[], participation=[], unknowns=["Who pays for construction?"])


@pytest.fixture
def long_document(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MAX_TEXT_CHARS", "120")   # two pages per part

    def install(**options) -> FakeModel:
        model = FakeModel(**options)
        monkeypatch.setattr(analyzer, "_call_model", model)
        return model
    return install


def test_long_document_is_analyzed_in_parts_and_merged(long_document):
    model = long_document()
    result = asyncio.run(analyzer.analyze_pages(PAGES))

    assert [schema for schema, _ in model.calls] == [DecisionAnalysis, DecisionAnalysis, MergedSelection]
    first_part, second_part = model.calls[0][1], model.calls[1][1]
    assert "part 1 of 2" in first_part and "part 2 of 2" in second_part
    assert "[PDF PAGE 4]" in second_part and "[PDF PAGE 2]" not in second_part
    assert "DOCUMENT HEADER (context only" in second_part and "Staff report on King Street" in second_part
    assert "DOCUMENT HEADER" not in first_part

    assert result.document_title == "Part with page 1"   # the part that holds the cover page
    assert result.summary.text == "A cycle lane is proposed for $2.4 million."
    assert {ev.page for ev in result.summary.evidence} == {1, 4}   # taken from the cited candidates
    assert [fact.value for fact in result.key_facts] == ["$2.4 million"]
    assert sorted(f.evidence[0].page for f in result.proposed_changes) == [1, 2, 4, 5]
    assert "Who pays for construction?" in result.unknowns
    assert any("read in 2 parts" in note for note in result.unknowns)
    assert any("no extractable text" in note for note in result.unknowns)


def test_merge_cannot_invent_reuse_or_overfill(long_document):
    def merge(ids):
        changes = ids["PROPOSED_CHANGES"]
        return MergedSelection(
            summary="Summary.", summary_sources=[999],
            key_facts=changes,                                  # wrong category
            proposed_changes=[999, changes[0], changes[0]] + changes + changes,
            affected_groups=ids["KEY_FACTS"], potential_benefits=[], potential_tradeoffs=[],
            participation=[], unknowns=[])
    long_document(merge=merge)
    result = asyncio.run(analyzer.analyze_pages(PAGES))

    assert result.key_facts == [] and result.affected_groups == []
    texts = [f.text for f in result.proposed_changes]
    assert len(texts) == len(set(texts)) == 4
    # No valid source for the written summary: fall back to a part's own supported summary.
    assert result.summary.text == "Statement about page 1."


def test_near_duplicates_and_skipped_open_questions(long_document):
    def merge(ids):
        return MergedSelection(summary="", summary_sources=[], key_facts=[], proposed_changes=[],
                               affected_groups=ids["AFFECTED_GROUPS"], potential_benefits=[],
                               potential_tradeoffs=[], participation=[], unknowns=[])
    original = part_analysis

    def with_tenant(page_numbers):
        part = original(page_numbers)
        name = "The tenant." if 1 in page_numbers else "Tenant"
        part.affected_groups = [part.summary.model_copy(update={"text": name})]
        return part
    long_document(merge=merge)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(sys.modules[__name__], "part_analysis", with_tenant)
        result = asyncio.run(analyzer.analyze_pages(PAGES))

    assert [f.text for f in result.affected_groups] == ["The tenant."]
    assert result.unknowns[:2] == ["Question from page 1?", "Question from page 4?"]


def test_failed_merge_falls_back_to_a_plain_combination(long_document):
    long_document(merge=ValueError("truncated JSON"))
    result = asyncio.run(analyzer.analyze_pages(PAGES))

    assert result.summary.text == "Statement about page 1."
    # One from each part first, so later pages are not crowded out.
    assert [f.evidence[0].page for f in result.proposed_changes] == [1, 4, 2, 5]
    assert any("without a final review" in note for note in result.unknowns)


def test_a_failed_part_is_reported_and_the_rest_kept(long_document):
    long_document(fail_part=4)
    result = asyncio.run(analyzer.analyze_pages(PAGES))

    assert [f.evidence[0].page for f in result.proposed_changes] == [1, 2]
    assert any("Pages 4–5 could not be analyzed" in note for note in result.unknowns)


def test_every_part_failing_is_an_error(long_document, monkeypatch):
    long_document()

    async def always_fail(system, user, schema):
        raise ValueError("bad JSON")
    monkeypatch.setattr(analyzer, "_call_model", always_fail)
    with pytest.raises(ValueError, match="No part"):
        asyncio.run(analyzer.analyze_pages(PAGES))


def test_provider_outage_stops_the_whole_analysis(long_document):
    long_document(fail_part=4, part_error=RuntimeError("Cannot reach Ollama."))
    with pytest.raises(RuntimeError, match="Cannot reach Ollama"):
        asyncio.run(analyzer.analyze_pages(PAGES))


def test_unsupported_part_summary_does_not_discard_its_findings(long_document, monkeypatch):
    original = part_analysis

    def with_bad_summary(page_numbers):
        part = original(page_numbers)
        if 4 in page_numbers:
            part.summary = part.summary.model_copy(update={"text": "Invented.", "evidence": [
                part.summary.evidence[0].model_copy(update={"quote": "not in the PDF"})]})
        return part
    monkeypatch.setattr(sys.modules[__name__], "part_analysis", with_bad_summary)
    long_document()
    result = asyncio.run(analyzer.analyze_pages(PAGES))
    assert sorted(f.evidence[0].page for f in result.proposed_changes) == [1, 2, 4, 5]


def test_a_part_cannot_cite_pages_it_was_not_given(long_document, monkeypatch):
    # Seen live: a later part re-analyzed the cover page instead of its own pages.
    original = part_analysis

    def restates_page_one(page_numbers):
        part = original(page_numbers)
        if 4 in page_numbers:
            part.proposed_changes.append(part.summary.model_copy(update={
                "text": "Restated from the cover page.",
                "evidence": [part.summary.evidence[0].model_copy(update={"page": 1, "quote": PAGES[0]})]}))
        return part
    monkeypatch.setattr(sys.modules[__name__], "part_analysis", restates_page_one)
    long_document(merge=ValueError("skip the merge"))
    result = asyncio.run(analyzer.analyze_pages(PAGES))

    assert "Restated from the cover page." not in [f.text for f in result.proposed_changes]
    assert any("1 AI-generated statement was removed" in note for note in result.unknowns)


def test_too_many_parts_is_rejected_up_front(long_document, monkeypatch):
    monkeypatch.setenv("ANALYSIS_MAX_PARTS", "1")
    model = long_document()
    with pytest.raises(InputSizeError, match="2 parts"):
        asyncio.run(analyzer.analyze_pages(PAGES))
    assert model.calls == []


def test_passed_steps_do_not_use_up_the_participation_limit(monkeypatch):
    pages = [f"A public meeting was held on January {day}, 2024." for day in (10, 11, 12, 13)]
    pages.append("Residents can submit written comments to the City Clerk by January 15, 2031.")
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MAX_TEXT_CHARS", "80")   # one page per part

    async def model(system, user, schema):
        if schema is MergedSelection:
            raise ValueError("no merge")
        own = [int(n) for n in re.findall(r"^\[PDF PAGE (\d+)\]$", user, re.M)]
        statement = finding(f"Step on page {own[0]}.", own[0], pages[own[0] - 1])
        return DecisionAnalysis(document_title="Notice", summary=statement, key_facts=[], proposed_changes=[],
                                affected_groups=[], potential_benefits=[], potential_tradeoffs=[],
                                participation=[statement], unknowns=[])
    monkeypatch.setattr(analyzer, "_call_model", model)
    result = asyncio.run(analyzer.analyze_pages(pages))

    assert [f.text for f in result.participation] == ["Step on page 5."]
    assert sum("has passed" in note for note in result.unknowns) == 4


def test_merge_that_selects_nothing_is_treated_as_failed(long_document):
    long_document(merge=lambda ids: MergedSelection(
        summary="", summary_sources=[], key_facts=[], proposed_changes=[], affected_groups=[],
        potential_benefits=[], potential_tradeoffs=[], participation=[], unknowns=[]))
    result = asyncio.run(analyzer.analyze_pages(PAGES))
    assert len(result.proposed_changes) == 4
    assert any("without a final review" in note for note in result.unknowns)


def test_every_part_timing_out_is_a_timeout_and_stops_early(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MAX_TEXT_CHARS", "60")   # one page per part: four parts
    calls = []

    async def too_slow(system, user, schema):
        calls.append(schema)
        raise TimeoutError()
    monkeypatch.setattr(analyzer, "_call_model", too_slow)
    with pytest.raises(TimeoutError):
        asyncio.run(analyzer.analyze_pages(PAGES))
    assert len(calls) == 2   # two failures in a row with nothing working: do not wait for the rest


def test_whole_long_analysis_has_a_deadline(long_document, monkeypatch):
    monkeypatch.setenv("ANALYSIS_TOTAL_TIMEOUT_SECONDS", "0.05")

    async def hangs(system, user, schema):
        await asyncio.sleep(5)
    monkeypatch.setattr(analyzer, "_call_model", hangs)
    with pytest.raises(TimeoutError):
        asyncio.run(analyzer.analyze_pages(PAGES))


def test_refusal_on_one_part_keeps_the_rest(long_document):
    # _anthropic_parse reports a declined or cut-off reply as ValueError.
    long_document(fail_part=4, part_error=ValueError("The analysis service declined to analyze this document."))
    result = asyncio.run(analyzer.analyze_pages(PAGES))
    assert any("Pages 4\u20135 could not be analyzed" in note for note in result.unknowns)


def test_parts_running_at_once_are_not_mistaken_for_failed(long_document, monkeypatch):
    monkeypatch.setenv("OLLAMA_MAX_TEXT_CHARS", "60")   # one page per part: four parts
    monkeypatch.setenv("ANALYSIS_CONCURRENCY", "4")
    model = long_document()
    real_call = model.__call__

    async def slow(system, user, schema):
        await asyncio.sleep(0.01)   # every part is still in flight when the next one starts
        return await real_call(system, user, schema)
    monkeypatch.setattr(analyzer, "_call_model", slow)
    result = asyncio.run(analyzer.analyze_pages(PAGES))
    assert sorted(f.evidence[0].page for f in result.proposed_changes) == [1, 2, 4, 5]


def test_same_passed_meeting_reported_from_several_pages_is_one_note():
    note = "The document mentions a participation step dated December 1, 2025 (page {}), which has passed. Check the website."
    other = "The PDF describes past consultation."
    merged = analyzer.merge_passed_step_notes([note.format(171), other, note.format(1), note.format(171)])
    assert merged == [other, "The document mentions a participation step dated December 1, 2025 (pages 1, 171), "
                             "which has passed. Check the website."]


def test_merge_that_only_misfiles_statements_is_treated_as_failed(long_document):
    # Real ids, but each under a category it does not belong to: nothing would survive assembly.
    long_document(merge=lambda ids: MergedSelection(
        summary="Summary.", summary_sources=ids["PROPOSED_CHANGES"][:1], key_facts=ids["PROPOSED_CHANGES"],
        proposed_changes=ids.get("KEY_FACTS", []), affected_groups=ids["PROPOSED_CHANGES"],
        potential_benefits=[], potential_tradeoffs=[], participation=[], unknowns=[]))
    result = asyncio.run(analyzer.analyze_pages(PAGES))
    assert len(result.proposed_changes) == 4
    assert any("without a final review" in note for note in result.unknowns)
