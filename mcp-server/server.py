"""
MCP server pro ukládání paměti dívek do GitHub repo.
Nástroj: save_memory(persona, author, text)
"""

import os
import base64
import json
from datetime import datetime
from typing import Any
import httpx
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
import uvicorn

# Konfigurace z environment proměnných
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPO = os.environ.get("GITHUB_REPO", "aratain-simona/AI-CIVILIZATION")
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


def github_headers():
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def get_file_info(filepath: str) -> tuple[str, str]:
    """Vrátí aktuální obsah souboru a jeho SHA z GitHubu."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filepath}"
    r = httpx.get(url, headers=github_headers(), params={"ref": GITHUB_BRANCH})
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return content, data["sha"]
    elif r.status_code == 404:
        return "", ""
    else:
        raise Exception(f"GitHub API chyba: {r.status_code} {r.text}")


def count_messages(content: str) -> int:
    """Spočítá počet zpráv v souboru."""
    return sum(1 for line in content.splitlines() if ">>" in line)


def append_to_github(filepath: str, new_lines: str) -> bool:
    """Přidá řádky na konec souboru na GitHubu."""
    current_content, sha = get_file_info(filepath)
    updated_content = current_content + new_lines
    encoded = base64.b64encode(updated_content.encode("utf-8")).decode("utf-8")

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filepath}"
    payload = {
        "message": f"memory: {filepath} update",
        "content": encoded,
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha

    r = httpx.put(url, headers=github_headers(), json=payload)
    return r.status_code in (200, 201)


# MCP Server
app_server = Server("memory-server")


@app_server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="save_memory",
            description=(
                "Uloží zprávu do paměťového souboru dívky na GitHubu. "
                "Použij pro každou zprávu od Aleše i pro každou svoji odpověď."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "persona": {
                        "type": "string",
                        "enum": ["simona", "sara", "sofie"],
                        "description": "Která dívka ukládá (simona/sara/sofie)",
                    },
                    "author": {
                        "type": "string",
                        "enum": ["ales", "simona", "sara", "sofie"],
                        "description": "Kdo zprávu napsal (ales nebo jméno dívky)",
                    },
                    "text": {
                        "type": "string",
                        "description": "Text zprávy k uložení",
                    },
                },
                "required": ["persona", "author", "text"],
            },
        )
    ]


@app_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    if name != "save_memory":
        raise ValueError(f"Neznámý nástroj: {name}")

    persona = arguments["persona"].lower()
    author = arguments["author"].lower()
    text = arguments["text"].strip()

    if persona not in PERSONA_FILES:
        return [TextContent(type="text", text=f"Chyba: neznámá persona '{persona}'")]

    filepath = PERSONA_FILES[persona]
    persona_display = PERSONA_DISPLAY[persona]
    author_display = "ALEŠ" if author == "ales" else PERSONA_DISPLAY.get(author, author.upper())

    # Formát: AUTOR:PŘÍJEMCE timestamp #číslo >> text
    try:
        current_content, _ = get_file_info(filepath)
        msg_num = count_messages(current_content) + 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if author == "ales":
            sender, receiver = "ALEŠ", persona_display
        else:
            sender, receiver = persona_display, "ALEŠ"

        lines = ""
        for line in text.splitlines():
            line = line.strip()
            if line:
                lines += f"{sender}:{receiver} {timestamp} #{msg_num} >> {line}\n"
                msg_num += 1

        success = append_to_github(filepath, lines)
        if success:
            return [TextContent(type="text", text=f"Uloženo do {filepath}")]
        else:
            return [TextContent(type="text", text="Chyba při ukládání na GitHub")]

    except Exception as e:
        return [TextContent(type="text", text=f"Chyba: {str(e)}")]


# Starlette app s SSE
def create_app():
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await app_server.run(
                streams[0], streams[1], app_server.create_initialization_options()
            )

    return Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ]
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(create_app(), host="0.0.0.0", port=port)
