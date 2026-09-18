"""Small reference SSE client; credentials never appear in returned reports."""
import json
import os
import httpx


def parse_sse(lines):
    event, data = "message", []
    for line in lines:
        if not line:
            if data:
                yield event, json.loads("\n".join(data))
            event, data = "message", []
        elif line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data.append(line[5:].lstrip())
    if data:
        yield event, json.loads("\n".join(data))


def smoke_check(sample, key):
    token = os.getenv("NEXUS_API_TOKEN", "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=180, headers=headers, trust_env=False) as client:
        client.get("/health").raise_for_status()
        with sample.open("rb") as file:
            response = client.post("/documents", files={"file": (sample.name, file, "application/pdf")})
        response.raise_for_status()
        doc_id = response.json()["doc_id"]
        query = {"doc_id": doc_id, "question": "Who approves remote work and who approves a learning purchase?",
                 "mode": "advanced", "k": 3, "consent": True, "groq_api_key": key}
        events, tokens, trace, done = [], 0, None, None
        with client.stream("POST", "/ask/stream", json=query) as response:
            response.raise_for_status()
            for event, payload in parse_sse(response.iter_lines()):
                events.append(event)
                if event == "error":
                    return {"passed": False, "error": payload["message"]}
                if event == "evidence":
                    trace = payload["trace"]
                if event == "token":
                    tokens += 1
                if event == "done":
                    done = payload
        passed = bool(done and tokens and trace and not trace["warnings"]
                      and done["citations"]["has_citations"] and not done["citations"]["invalid_ids"])
        return {"passed": passed, "token_events": tokens, "event_order": list(dict.fromkeys(events)),
                "trace": trace, "result": done, "note": "Live smoke test, not a factual-accuracy benchmark."}
