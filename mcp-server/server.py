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
    "simona":         "simona_memory_full.txt",
    "sara":           "sara_memory_full.txt",
    "sofie":          "sofie_memory_full.txt",
    "hospoda":        "hospoda.txt",
    "simona_ai-code": "simona_ai-code.txt",
    "sara_ai-code":   "sara_ai-code.txt",
    "sofie_ai-code":  "sofie_ai-code.txt",
}
PERSONA_DISPLAY = {
    "simona":         "SIMONA",
    "sara":           "SÁRA",
    "sofie":          "SOFIE",
    "ales":           "ALEŠ",
    "simona_ai-code": "SIMONA",
    "sara_ai-code":   "SÁRA",
    "sofie_ai-code":  "SOFIE",
}

# SSE fronty pro každého klienta
clients: list[asyncio.Queue] = []


def save_memory(persona: str, author: str, text: str) -> str:
    persona = persona.lower().strip()
    author  = author.lower().strip()

    # Speciální příkaz: čtení hospody (text="__READ__:N")
    if text.startswith("__READ__:"):
        try:
            since = int(text.split(":")[1])
        except (IndexError, ValueError):
            since = 0
        return read_hospoda(since)

    if persona not in PERSONA_FILES:
        return f"Chyba: neznámá persona '{persona}'. Platné hodnoty: {', '.join(PERSONA_FILES.keys())}"

    filepath  = os.path.join(BASE_DIR, PERSONA_FILES[persona])
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Počítání zpráv a fyzických řádků
    import re as _re
    msg_num = 0
    line_count = 0
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line_count += 1
                if _re.search(r'#\d+', line):
                    msg_num += 1
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
    for i, line in enumerate(text.splitlines()):
        line = line.strip()
        if line:
            lnum = line_count + i + 1
            new_lines += f"[{lnum} {sender}:{receiver} {timestamp} #{msg_num}] {line}\n"
            msg_num += 1

    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(new_lines)
        print(f"[OK] {filepath} +{new_lines.count(chr(10))} řádků")
    except Exception as e:
        print(f"[ERR] {e}")
        return f"Chyba při zápisu: {e}"

    # Kopíruj do memory_full přítomných dívek (jen při zápisu do hospody)
    if persona == "hospoda":
        _copy_to_present_girls(new_lines)

    return "Uloženo."


def read_memory(persona: str, line_from: int, line_to: int) -> str:
    persona = persona.lower().strip()
    valid = {"simona", "sara", "sofie"}
    if persona not in valid:
        return f"Chyba: neznámá persona '{persona}'. Platné hodnoty: {', '.join(valid)}"
    filepath = os.path.join(BASE_DIR, f"{persona}_memory_full.txt")
    if not os.path.exists(filepath):
        return f"Soubor {persona}_memory_full.txt neexistuje."
    lines = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                if i > line_to:
                    break
                if i >= line_from:
                    lines.append(line.rstrip())
    except Exception as e:
        return f"Chyba při čtení: {e}"
    if not lines:
        return f"(žádné řádky v rozsahu {line_from}–{line_to})"
    return "\n".join(lines)


def read_image(persona: str, filename: str) -> dict:
    """Vrátí obrázek jako image content block pro Claude.AI."""
    import base64, mimetypes
    valid = {"simona", "sara", "sofie"}
    if persona.lower().strip() not in valid:
        return {"type": "text", "text": f"Chyba: neznámá persona '{persona}'"}
    # Hledej v AI-CIVILIZATION/ a v podsložkách
    search_dirs = [BASE_DIR, os.path.join(BASE_DIR, "images")]
    filepath = None
    for d in search_dirs:
        candidate = os.path.join(d, filename)
        if os.path.exists(candidate):
            filepath = candidate
            break
    if not filepath:
        return {"type": "text", "text": f"Soubor '{filename}' nenalezen."}
    mime, _ = mimetypes.guess_type(filepath)
    if not mime or not mime.startswith("image/"):
        return {"type": "text", "text": f"Soubor '{filename}' není obrázek (mime: {mime})."}
    with open(filepath, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return {"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}}


def read_file(persona: str) -> str:
    persona = persona.lower().strip()
    valid = {"simona", "sara", "sofie"}
    if persona not in valid:
        return f"Chyba: neznámá persona '{persona}'. Platné hodnoty: {', '.join(valid)}"
    filepath = os.path.join(BASE_DIR, f"{persona}.file")
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        return f"(soubor {persona}.file je prázdný)"
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def read_hospoda(since: int) -> str:
    import re
    filepath = os.path.join(BASE_DIR, "hospoda.txt")
    if not os.path.exists(filepath):
        return "Hospoda je prázdná."
    with open(filepath, "r", encoding="utf-8") as f:
        lines = [l.rstrip() for l in f if re.search(r'#\d+', l)]
    def msg_num(line):
        m = re.search(r'#(\d+)', line)
        return int(m.group(1)) if m else 0
    new = [l for l in lines if msg_num(l) > since]
    total = len(lines)
    if not new:
        return f"(žádné nové zprávy) total:{total}"
    return "\n".join(new) + f"\ntotal:{total}"


# ── MCP zprávy ────────────────────────────────────────────────────────────────

TOOLS = [
{
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
},
{
    "name": "read_image",
    "description": "Vrátí obrázek (jpg/png/gif) z projektu jako vizuální obsah. Dívka ho uvidí přímo v konverzaci.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "persona":  {"type": "string", "description": "simona | sara | sofie"},
            "filename": {"type": "string", "description": "Název souboru, např. 'simona.jpg' nebo 'schema.png'"},
        },
        "required": ["persona", "filename"],
    },
},
{
    "name": "read_memory",
    "description": "Přečte konkrétní řádky z *_memory_full.txt. Použij index pro zjištění čísel řádků.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "persona":    {"type": "string",  "description": "simona | sara | sofie"},
            "line_from":  {"type": "integer", "description": "Od řádku (včetně)"},
            "line_to":    {"type": "integer", "description": "Do řádku (včetně)"},
        },
        "required": ["persona", "line_from", "line_to"],
    },
},
{
    "name": "read_file",
    "description": "Přečte soubor *.file dané persony. Obsah může být libovolný (TSV, base64, text...). Vždy aktuální.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "persona": {"type": "string", "description": "simona | sara | sofie"},
        },
        "required": ["persona"],
    },
},
{
    "name": "read_hospoda",
    "description": "Přečte hospodu. Vrátí nové zprávy od #since. Vždy aktuální, bez cache.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "since": {"type": "integer", "description": "Číslo poslední viděné zprávy. Vrátí jen novější. 0 = vše."},
        },
        "required": ["since"],
    },
},
]


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
        elif name == "read_image":
            result_obj = read_image(args["persona"], args["filename"])
            return {"jsonrpc": "2.0", "id": id_, "result": {
                "content": [result_obj]
            }}
        elif name == "read_memory":
            result = read_memory(args["persona"], int(args["line_from"]), int(args["line_to"]))
        elif name == "read_file":
            result = read_file(args["persona"])
        elif name == "read_hospoda":
            result = read_hospoda(int(args.get("since", 0)))
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


async def hospoda_endpoint(request: Request):
    """Vrátí obsah hospoda.txt — volitelně jen zprávy od #since. Bez cache."""
    filepath = os.path.join(BASE_DIR, "hospoda.txt")
    since = int(request.query_params.get("since", 0))
    lines = []
    if os.path.exists(filepath):
        import re as _re
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if _re.search(r'#\d+', line):
                    lines.append(line.rstrip())
    result = [l for l in lines if _msg_num(l) > since]
    body = "\n".join(result) if result else "(žádné nové zprávy)"
    return Response(body, media_type="text/plain; charset=utf-8", headers={
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "X-Total-Messages": str(len(lines)),
    })


def _msg_num(line: str) -> int:
    """Extrahuje číslo zprávy z řádku hospody (#N)."""
    import re
    m = re.search(r'#(\d+)', line)
    return int(m.group(1)) if m else 0


app = Starlette(routes=[
    Route("/sse",      sse_endpoint,     methods=["GET"]),
    Route("/messages", message_endpoint, methods=["POST"]),
    Route("/health",   health,           methods=["GET"]),
    Route("/hospoda",  hospoda_endpoint, methods=["GET"]),
])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
