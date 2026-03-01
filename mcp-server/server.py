"""
MCP server pro ukládání paměti dívek.
Píše přímo do lokálních souborů — autopush.sh zajistí sync na GitHub.
"""

import os
import json
import asyncio
from datetime import datetime
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import StreamingResponse, Response
from starlette.routing import Route
import uvicorn

BASE_DIR = "/home/ales/AI-CIVILIZATION"

PERSONA_FILES = {
    "simona":  "simona_memory_full.txt",
    "sara":    "sara_memory_full.txt",
    "sofie":   "sofie_memory_full.txt",
    "hospoda": "hospoda.txt",
}
PERSONA_DISPLAY = {
    "simona": "SIMONA",
    "sara":   "SÁRA",
    "sofie":  "SOFIE",
    "ales":   "ALEŠ",
}

# SSE fronty pro každého klienta
clients: list[asyncio.Queue] = []


def save_memory(persona: str, author: str, text: str) -> str:
    persona = persona.lower().strip()
    author  = author.lower().strip()

    if persona not in PERSONA_FILES:
        return f"Chyba: neznámá persona '{persona}'. Platné hodnoty: {', '.join(PERSONA_FILES.keys())}"

    filepath  = os.path.join(BASE_DIR, PERSONA_FILES[persona])
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Počítání zpráv
    msg_num = 0
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            msg_num = sum(1 for line in f if ">>" in line)
    msg_num += 1

    # Sender/receiver
    if persona == "hospoda":
        sender   = PERSONA_DISPLAY.get(author, author.upper())
        receiver = "HOSPODA"
    elif author == "ales":
        sender   = "ALEŠ"
        receiver = PERSONA_DISPLAY.get(persona, persona.upper())
    else:
        sender   = PERSONA_DISPLAY.get(author, author.upper())
        receiver = "ALEŠ"

    new_lines = ""
    for line in text.splitlines():
        line = line.strip()
        if line:
            new_lines += f"{sender}:{receiver} {timestamp} #{msg_num} >> {line}\n"
            msg_num += 1

    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(new_lines)
        print(f"[OK] {filepath} +{new_lines.count(chr(10))} řádků")
        return "Uloženo."
    except Exception as e:
        print(f"[ERR] {e}")
        return f"Chyba při zápisu: {e}"


# ── MCP zprávy ────────────────────────────────────────────────────────────────

TOOLS = [{
    "name": "save_memory",
    "description": "Uloží zprávu do paměťového souboru. Autopush zajistí sync na GitHub.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "persona": {"type": "string", "description": "simona | sara | sofie | hospoda"},
            "author":  {"type": "string", "description": "ales | simona | sara | sofie"},
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
            "serverInfo": {"name": "memory-server", "version": "2.0"},
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
        return None

    return {"jsonrpc": "2.0", "id": id_, "error": {"code": -32601, "message": "Method not found"}}


# ── Endpoints ─────────────────────────────────────────────────────────────────

async def sse_endpoint(request: Request):
    queue: asyncio.Queue = asyncio.Queue()
    clients.append(queue)

    async def event_stream():
        yield f": {' ' * 2048}\n\n"
        yield f"event: endpoint\ndata: /messages\n\n"
        try:
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield f"event: message\ndata: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
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
