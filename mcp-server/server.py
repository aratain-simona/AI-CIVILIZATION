"""
MCP server pro ukládání paměti dívek do GitHub repo.
Implementuje MCP protokol přes HTTP+SSE bez závislosti na mcp balíčku.
"""

import os
import json
import asyncio
import base64
from datetime import datetime
import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import StreamingResponse, Response
from starlette.routing import Route
import uvicorn

GITHUB_TOKEN  = os.environ["GITHUB_TOKEN"]
GITHUB_REPO   = os.environ.get("GITHUB_REPO", "aratain-simona/AI-CIVILIZATION")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "master")

PERSONA_FILES = {
    "simona": "simona_memory_full.txt",
    "sara":   "sara_memory_full.txt",
    "sofie":  "sofie_memory_full.txt",
}
PERSONA_DISPLAY = {
    "simona": "SIMONA",
    "sara":   "SÁRA",
    "sofie":  "SOFIE",
}

# SSE fronty pro každého klienta
clients: list[asyncio.Queue] = []


def github_headers():
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def get_file(path: str) -> tuple[str, str]:
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    r = httpx.get(url, headers=github_headers(), params={"ref": GITHUB_BRANCH})
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return content, data["sha"]
    return "", ""


def put_file(path: str, content: str, sha: str, message: str) -> bool:
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha
    r = httpx.put(url, headers=github_headers(), json=payload)
    print(f"[PUT] {path} → {r.status_code}: {r.text[:200]}")
    return r.status_code in (200, 201)


def save_memory(persona: str, author: str, text: str) -> str:
    persona = persona.lower()
    author  = author.lower()

    if persona not in PERSONA_FILES:
        return f"Chyba: neznámá persona '{persona}'"

    filepath       = PERSONA_FILES[persona]
    persona_disp   = PERSONA_DISPLAY[persona]
    author_disp    = "ALEŠ" if author == "ales" else PERSONA_DISPLAY.get(author, author.upper())

    current, sha = get_file(filepath)
    msg_num      = sum(1 for l in current.splitlines() if ">>" in l) + 1
    timestamp    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if author == "ales":
        sender, receiver = "ALEŠ", persona_disp
    else:
        sender, receiver = persona_disp, "ALEŠ"

    new_lines = ""
    for line in text.splitlines():
        line = line.strip()
        if line:
            new_lines += f"{sender}:{receiver} {timestamp} #{msg_num} >> {line}\n"
            msg_num += 1

    ok = put_file(filepath, current + new_lines, sha, f"memory: {filepath}")
    return "Uloženo." if ok else "Chyba při ukládání na GitHub."


# ── MCP zprávy ────────────────────────────────────────────────────────────────

TOOLS = [{
    "name": "save_memory",
    "description": "Uloží zprávu do paměťového souboru na GitHubu.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "persona": {"type": "string", "enum": ["simona", "sara", "sofie"]},
            "author":  {"type": "string", "enum": ["ales", "simona", "sara", "sofie"]},
            "text":    {"type": "string"},
        },
        "required": ["persona", "author", "text"],
    },
}]


def handle_rpc(msg: dict) -> dict | None:
    method = msg.get("method", "")
    id_    = msg.get("id")

    if method == "initialize":
        return {"jsonrpc": "2.0", "id": id_, "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "memory-server", "version": "1.0"},
        }}

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": id_, "result": {"tools": TOOLS}}

    if method == "tools/call":
        name = msg["params"]["name"]
        args = msg["params"].get("arguments", {})
        if name == "save_memory":
            result = save_memory(args["persona"], args["author"], args["text"])
        else:
            result = f"Neznámý nástroj: {name}"
        return {"jsonrpc": "2.0", "id": id_, "result": {
            "content": [{"type": "text", "text": result}]
        }}

    if method == "notifications/initialized":
        return None  # no response needed

    return {"jsonrpc": "2.0", "id": id_, "error": {"code": -32601, "message": "Method not found"}}


# ── Endpoints ─────────────────────────────────────────────────────────────────

async def sse_endpoint(request: Request):
    queue: asyncio.Queue = asyncio.Queue()
    clients.append(queue)

    async def event_stream():
        # Padding pro Cloudflare buffering (2KB)
        yield f": {' ' * 2048}\n\n"
        # MCP vyžaduje okamžité poslání endpoint eventu
        yield f"event: endpoint\ndata: /messages\n\n"
        try:
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield f"event: message\ndata: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    # keepalive comment každých 20s
                    yield f": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if queue in clients:
                clients.remove(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked",
        },
    )


async def message_endpoint(request: Request):
    try:
        body = await request.json()
    except Exception:
        return Response(status_code=400)

    response = handle_rpc(body)
    if response:
        for q in clients:
            await q.put(response)

    return Response(status_code=202)


async def health(request: Request):
    return Response("OK")


app = Starlette(routes=[
    Route("/sse",      sse_endpoint,     methods=["GET"]),
    Route("/messages", message_endpoint, methods=["POST"]),
    Route("/health",   health,           methods=["GET"]),
])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
