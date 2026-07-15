import asyncio
import json

import pytest
from redis.exceptions import ConnectionError, TimeoutError

from axiom_core.enums import JobStatus
from packages.axiom_research import queue_worker as qw


class DummyListener:
    def __init__(self, messages):
        self._messages = iter(messages)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._messages)
        except StopIteration:
            raise StopAsyncIteration

    async def aclose(self):
        return None


class DummyPubSub:
    def __init__(self, messages):
        self.messages = messages
        self.subscribed = []
        self.unsubscribed = []
        self.closed = False

    async def subscribe(self, channel):
        self.subscribed.append(channel)

    async def unsubscribe(self, channel):
        self.unsubscribed.append(channel)

    async def aclose(self):
        self.closed = True

    def listen(self):
        return DummyListener(self.messages)


class DummyClient:
    def __init__(self):
        self.hashes = {}
        self.queue = []
        self.published = []
        self.pubsub_instance = None
        self.blpop_items = []
        self.blpop_error = None

    async def hset(self, key, field, value):
        self.hashes.setdefault(key, {})[field] = value

    async def hget(self, key, field):
        return self.hashes.get(key, {}).get(field)

    async def hvals(self, key):
        return list(self.hashes.get(key, {}).values())

    async def rpush(self, key, value):
        self.queue.append((key, value))

    async def publish(self, channel, msg):
        self.published.append((channel, msg))

    async def blpop(self, key, timeout=0):
        if self.blpop_error is not None:
            err = self.blpop_error
            self.blpop_error = None
            raise err
        if self.blpop_items:
            return self.blpop_items.pop(0)
        return None

    def pubsub(self):
        return self.pubsub_instance


class DummyValkey:
    def __init__(self, client):
        self.client = client


class DummyFinding:
    def __init__(self, sub_query, summary):
        self.sub_query = sub_query
        self.summary = summary


class DummyResult:
    def __init__(self, report, findings):
        self.report = report
        self.findings = findings


class SuccessLoop:
    def __init__(self, driver):
        self.driver = driver

    async def run(self, question, **kwargs):
        return DummyResult(
            report=f"report for {question}",
            findings=[
                DummyFinding("sub-1", "summary 1"),
                DummyFinding("sub-2", "summary 2"),
            ],
        )


class FailureLoop:
    def __init__(self, driver):
        self.driver = driver

    async def run(self, question, **kwargs):
        raise RuntimeError("loop failed")


@pytest.mark.unit
def test_channel_formats_job_stream_channel():
    assert qw._channel("job-123") == "axiom:stream:job-123"


@pytest.mark.unit
def test_now_returns_isoformat_string():
    ts = qw._now()
    assert isinstance(ts, str)
    assert "T" in ts


@pytest.mark.unit
@pytest.mark.asyncio
async def test_jobstore_create_get_list_and_update(monkeypatch):
    client = DummyClient()
    store = qw.JobStore(DummyValkey(client))

    ids = iter(["job-a", "job-b"])
    monkeypatch.setattr(qw.uuid, "uuid4", lambda: next(ids))
    monkeypatch.setattr(qw, "_now", lambda: "2026-07-15T12:00:00+00:00")

    created_1 = await store.create("Question A")
    created_2 = await store.create("Question B")

    assert created_1 == "job-a"
    assert created_2 == "job-b"

    job_a = await store.get("job-a")
    assert job_a["question"] == "Question A"
    assert job_a["status"] == JobStatus.QUEUED.value

    all_jobs = await store.list_all()
    assert [j["id"] for j in all_jobs] == ["job-a", "job-b"]

    await store.update("job-a", status=JobStatus.RUNNING.value, report="partial")
    updated = await store.get("job-a")
    assert updated["status"] == JobStatus.RUNNING.value
    assert updated["report"] == "partial"
    assert updated["updated_at"] == "2026-07-15T12:00:00+00:00"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_jobstore_update_missing_job_is_noop():
    client = DummyClient()
    store = qw.JobStore(DummyValkey(client))

    await store.update("missing", status="done")

    assert client.hashes == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enqueue_creates_job_and_pushes_queue(monkeypatch):
    client = DummyClient()
    worker = qw.QueueWorker(driver=object(), valkey=DummyValkey(client))

    async def fake_create(question):
        assert question == "What is Axiom?"
        return "job-1"

    worker._store.create = fake_create

    job_id = await worker.enqueue("What is Axiom?")

    assert job_id == "job-1"
    assert client.queue == [(qw.QUEUE_KEY, "job-1")]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_emits_json_event(monkeypatch):
    client = DummyClient()
    worker = qw.QueueWorker(driver=object(), valkey=DummyValkey(client))
    monkeypatch.setattr(qw, "_now", lambda: "2026-07-15T12:00:00+00:00")

    await worker._publish("job-9", "status", {"status": "running"})

    assert len(client.published) == 1
    channel, payload = client.published[0]
    assert channel == "axiom:stream:job-9"
    data = json.loads(payload)
    assert data == {
        "event": "status",
        "data": {"status": "running"},
        "ts": "2026-07-15T12:00:00+00:00",
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_success_updates_store_and_publishes(monkeypatch):
    client = DummyClient()
    worker = qw.QueueWorker(driver=object(), valkey=DummyValkey(client))

    events = []
    updates = []

    async def fake_publish(job_id, event, data):
        events.append((job_id, event, data))

    async def fake_update(job_id, **fields):
        updates.append((job_id, fields))

    async def fake_get(job_id):
        return {"id": job_id, "question": "What is Axiom?"}

    monkeypatch.setattr(qw, "ResearchLoop", SuccessLoop)
    worker._publish = fake_publish
    worker._store.update = fake_update
    worker._store.get = fake_get

    class DummySettings:
        axiom_breadth = 4

    monkeypatch.setattr(qw, "settings", DummySettings())

    await worker._process("job-1")

    assert updates[0] == ("job-1", {"status": JobStatus.RUNNING.value})
    assert updates[-1] == (
        "job-1",
        {"status": JobStatus.DONE.value, "report": "report for What is Axiom?"},
    )

    assert events[0] == ("job-1", "status", {"status": "running"})
    assert events[1] == ("job-1", "progress", {"msg": "Planning sub-queries"})
    assert events[2] == (
        "job-1",
        "finding",
        {"index": 1, "sub_query": "sub-1", "summary": "summary 1"},
    )
    assert events[3] == (
        "job-1",
        "finding",
        {"index": 2, "sub_query": "sub-2", "summary": "summary 2"},
    )
    assert events[-1] == (
        "job-1",
        "done",
        {"status": "done", "report": "report for What is Axiom?"},
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_failure_updates_store_and_publishes_error(monkeypatch):
    client = DummyClient()
    worker = qw.QueueWorker(driver=object(), valkey=DummyValkey(client))

    events = []
    updates = []

    async def fake_publish(job_id, event, data):
        events.append((job_id, event, data))

    async def fake_update(job_id, **fields):
        updates.append((job_id, fields))

    async def fake_get(job_id):
        return {"id": job_id, "question": "What is Axiom?"}

    monkeypatch.setattr(qw, "ResearchLoop", FailureLoop)
    worker._publish = fake_publish
    worker._store.update = fake_update
    worker._store.get = fake_get

    class DummySettings:
        axiom_breadth = 4

    monkeypatch.setattr(qw, "settings", DummySettings())

    await worker._process("job-2")

    assert updates[0] == ("job-2", {"status": JobStatus.RUNNING.value})
    assert updates[-1] == ("job-2", {"status": JobStatus.FAILED.value, "error": "loop failed"})
    assert events[0] == ("job-2", "status", {"status": "running"})
    assert events[1] == ("job-2", "progress", {"msg": "Planning sub-queries"})
    assert events[-1] == ("job-2", "error", {"error": "loop failed"})


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_forever_processes_job_then_stops():
    client = DummyClient()
    client.blpop_items = [("axiom:queue", "job-3")]
    worker = qw.QueueWorker(driver=object(), valkey=DummyValkey(client))

    seen = []

    async def fake_process(job_id):
        seen.append(job_id)
        worker.stop()

    worker._process = fake_process

    await worker.run_forever()

    assert seen == ["job-3"]
    assert worker._running is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_forever_ignores_none_then_stops():
    client = DummyClient()
    worker = qw.QueueWorker(driver=object(), valkey=DummyValkey(client))

    calls = {"count": 0}

    async def fake_blpop(key, timeout=0):
        calls["count"] += 1
        if calls["count"] == 1:
            return None
        worker.stop()
        return None

    client.blpop = fake_blpop

    await worker.run_forever()

    assert calls["count"] == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_forever_breaks_on_cancelled_error():
    client = DummyClient()
    worker = qw.QueueWorker(driver=object(), valkey=DummyValkey(client))

    async def fake_blpop(key, timeout=0):
        raise asyncio.CancelledError()

    client.blpop = fake_blpop

    await worker.run_forever()

    assert worker._running is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_forever_sleeps_on_connection_or_timeout(monkeypatch):
    client = DummyClient()
    worker = qw.QueueWorker(driver=object(), valkey=DummyValkey(client))

    slept = []

    async def fake_sleep(seconds):
        slept.append(seconds)
        worker.stop()

    monkeypatch.setattr(qw.asyncio, "sleep", fake_sleep)
    client.blpop_error = ConnectionError("down")

    await worker.run_forever()
    assert slept == [2]

    client.blpop_error = TimeoutError("slow")
    worker._running = False

    async def fake_sleep_2(seconds):
        slept.append(seconds)
        worker.stop()

    monkeypatch.setattr(qw.asyncio, "sleep", fake_sleep_2)
    await worker.run_forever()
    assert slept[-1] == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_forever_sleeps_on_unexpected_exception(monkeypatch):
    client = DummyClient()
    worker = qw.QueueWorker(driver=object(), valkey=DummyValkey(client))

    slept = []

    async def fake_sleep(seconds):
        slept.append(seconds)
        worker.stop()

    monkeypatch.setattr(qw.asyncio, "sleep", fake_sleep)

    async def fake_blpop(key, timeout=0):
        raise RuntimeError("boom")

    client.blpop = fake_blpop

    await worker.run_forever()

    assert slept == [1]


@pytest.mark.unit
def test_stop_sets_running_false():
    worker = qw.QueueWorker(driver=object(), valkey=DummyValkey(DummyClient()))
    worker._running = True

    worker.stop()

    assert worker._running is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sse_stream_yields_existing_done_status_and_exits():
    client = DummyClient()
    job_id = "job-7"
    client.hashes[qw.JOBS_KEY] = {
        job_id: json.dumps({"id": job_id, "status": JobStatus.DONE.value})
    }
    client.pubsub_instance = DummyPubSub(messages=[])

    chunks = []
    async for chunk in qw.sse_stream(DummyValkey(client), job_id):
        chunks.append(chunk)

    assert len(chunks) == 2
    assert '"event": "status"' in chunks[0]
    assert '"status": "done"' in chunks[0]
    assert '"event": "done"' in chunks[1]
    assert '"status": "done"' in chunks[1]
    assert client.pubsub_instance.subscribed == ["axiom:stream:job-7"]
    assert client.pubsub_instance.unsubscribed == ["axiom:stream:job-7"]
    assert client.pubsub_instance.closed is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sse_stream_yields_messages_until_done():
    client = DummyClient()
    job_id = "job-8"
    client.hashes[qw.JOBS_KEY] = {
        job_id: json.dumps({"id": job_id, "status": JobStatus.RUNNING.value})
    }
    client.pubsub_instance = DummyPubSub(
        messages=[
            {"type": "subscribe", "data": 1},
            {"type": "message", "data": json.dumps({"event": "progress", "data": {"msg": "step"}})},
            {"type": "message", "data": json.dumps({"event": "done", "data": {"status": "done"}})},
        ]
    )

    chunks = []
    async for chunk in qw.sse_stream(DummyValkey(client), job_id):
        chunks.append(chunk)

    assert len(chunks) == 3
    assert '"status": "running"' in chunks[0]
    assert '"event": "progress"' in chunks[1]
    assert '"event": "done"' in chunks[2]
    assert client.pubsub_instance.closed is True
