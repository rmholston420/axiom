import types

import pytest

from packages.axiom_research import loop as loop_module
from packages.axiom_research.loop import ResearchLoop


class DummyPlanner:
    def __init__(self, ollama):
        self.ollama = ollama
        self.calls = []

    async def plan(self, question, breadth=None):
        self.calls.append((question, breadth))
        return [
            types.SimpleNamespace(text="subquery one"),
            types.SimpleNamespace(text="subquery two"),
        ]


class DummyPlannerEmpty:
    def __init__(self, ollama):
        self.ollama = ollama
        self.calls = []

    async def plan(self, question, breadth=None):
        self.calls.append((question, breadth))
        return []


class DummyRetriever:
    def __init__(self, searxng):
        self.searxng = searxng
        self.calls = []

    async def retrieve(self, text):
        self.calls.append(text)
        if text == "subquery one":
            return [
                types.SimpleNamespace(url="https://a.test", title="A"),
                types.SimpleNamespace(url="https://b.test", title="B"),
            ]
        return [
            types.SimpleNamespace(url="https://c.test", title="C"),
        ]


class DummyExtractor:
    def __init__(self, ollama):
        self.ollama = ollama
        self.calls = []

    async def extract(self, subquery, results):
        self.calls.append((subquery, [r.url for r in results]))
        return f"summary for {subquery}"


class DummySynthesizer:
    def __init__(self, ollama):
        self.ollama = ollama
        self.calls = []

    async def synthesize(self, question, findings):
        self.calls.append((question, findings))
        return f"report for {question} ({len(findings)} findings)"


class DummyRepo:
    instances = []

    def __init__(self, driver):
        self.driver = driver
        self.create_query_calls = []
        self.upsert_source_calls = []
        self.create_finding_calls = []
        DummyRepo.instances.append(self)

    async def create_query(self, question, job_id=None):
        self.create_query_calls.append((question, job_id))
        return "query-123"

    async def upsert_source(self, url, title):
        self.upsert_source_calls.append((url, title))

    async def create_finding(self, query_id, sub_query, summary, source_urls):
        self.create_finding_calls.append((query_id, sub_query, summary, source_urls))


@pytest.mark.unit
def test_research_loop_constructor_wires_dependencies(monkeypatch):
    ollama_obj = object()
    searxng_obj = object()

    monkeypatch.setattr(loop_module, "OllamaProvider", lambda: ollama_obj)
    monkeypatch.setattr(loop_module, "SearxngProvider", lambda: searxng_obj)
    monkeypatch.setattr(loop_module, "Planner", DummyPlanner)
    monkeypatch.setattr(loop_module, "Retriever", DummyRetriever)
    monkeypatch.setattr(loop_module, "Extractor", DummyExtractor)
    monkeypatch.setattr(loop_module, "Synthesizer", DummySynthesizer)

    loop = ResearchLoop(driver="driver-x")

    assert loop._driver == "driver-x"
    assert loop._ollama is ollama_obj
    assert loop._searxng is searxng_obj
    assert isinstance(loop._planner, DummyPlanner)
    assert isinstance(loop._retriever, DummyRetriever)
    assert isinstance(loop._extractor, DummyExtractor)
    assert isinstance(loop._synthesizer, DummySynthesizer)
    assert loop._planner.ollama is ollama_obj
    assert loop._retriever.searxng is searxng_obj
    assert loop._extractor.ollama is ollama_obj
    assert loop._synthesizer.ollama is ollama_obj


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_executes_full_pipeline(monkeypatch):
    ensure_calls = []

    async def fake_ensure_schema(driver):
        ensure_calls.append(driver)

    DummyRepo.instances = []
    monkeypatch.setattr(loop_module, "ensure_schema", fake_ensure_schema)
    monkeypatch.setattr(loop_module, "GraphRepository", DummyRepo)
    monkeypatch.setattr(loop_module, "Planner", DummyPlanner)
    monkeypatch.setattr(loop_module, "Retriever", DummyRetriever)
    monkeypatch.setattr(loop_module, "Extractor", DummyExtractor)
    monkeypatch.setattr(loop_module, "Synthesizer", DummySynthesizer)
    monkeypatch.setattr(loop_module, "OllamaProvider", lambda: object())
    monkeypatch.setattr(loop_module, "SearxngProvider", lambda: object())

    loop = ResearchLoop(driver="driver-x")
    result = await loop.run("What is Axiom?", job_id="job-7", breadth=3)

    repo = DummyRepo.instances[-1]

    assert ensure_calls == ["driver-x"]
    assert repo.create_query_calls == [("What is Axiom?", "job-7")]
    assert loop._planner.calls == [("What is Axiom?", 3)]
    assert loop._retriever.calls == ["subquery one", "subquery two"]
    assert loop._extractor.calls == [
        ("subquery one", ["https://a.test", "https://b.test"]),
        ("subquery two", ["https://c.test"]),
    ]
    assert repo.upsert_source_calls == [
        ("https://a.test", "A"),
        ("https://b.test", "B"),
        ("https://c.test", "C"),
    ]
    assert repo.create_finding_calls == [
        (
            "query-123",
            "subquery one",
            "summary for subquery one",
            ["https://a.test", "https://b.test"],
        ),
        ("query-123", "subquery two", "summary for subquery two", ["https://c.test"]),
    ]
    assert result.query == "What is Axiom?"
    assert result.query_id == "query-123"
    assert len(result.findings) == 2
    assert result.findings[0].sub_query == "subquery one"
    assert result.findings[0].summary == "summary for subquery one"
    assert result.findings[0].source_urls == ["https://a.test", "https://b.test"]
    assert result.findings[1].sub_query == "subquery two"
    assert result.report == "report for What is Axiom? (2 findings)"
    synth_question, synth_findings = loop._synthesizer.calls[0]
    assert synth_question == "What is Axiom?"
    assert len(synth_findings) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_handles_empty_plan(monkeypatch):
    ensure_calls = []

    async def fake_ensure_schema(driver):
        ensure_calls.append(driver)

    DummyRepo.instances = []
    monkeypatch.setattr(loop_module, "ensure_schema", fake_ensure_schema)
    monkeypatch.setattr(loop_module, "GraphRepository", DummyRepo)
    monkeypatch.setattr(loop_module, "Planner", DummyPlannerEmpty)
    monkeypatch.setattr(loop_module, "Retriever", DummyRetriever)
    monkeypatch.setattr(loop_module, "Extractor", DummyExtractor)
    monkeypatch.setattr(loop_module, "Synthesizer", DummySynthesizer)
    monkeypatch.setattr(loop_module, "OllamaProvider", lambda: object())
    monkeypatch.setattr(loop_module, "SearxngProvider", lambda: object())

    loop = ResearchLoop(driver="driver-y")
    result = await loop.run("Empty question", job_id=None, breadth=1)

    repo = DummyRepo.instances[-1]

    assert ensure_calls == ["driver-y"]
    assert repo.create_query_calls == [("Empty question", None)]
    assert loop._planner.calls == [("Empty question", 1)]
    assert loop._retriever.calls == []
    assert loop._extractor.calls == []
    assert repo.upsert_source_calls == []
    assert repo.create_finding_calls == []
    assert result.query == "Empty question"
    assert result.query_id == "query-123"
    assert result.findings == []
    assert result.report == "report for Empty question (0 findings)"
