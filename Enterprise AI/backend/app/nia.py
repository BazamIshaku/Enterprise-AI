"""Local Ollama provider used by NIA conversations."""
import json
import os
from collections.abc import AsyncIterator
import httpx

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
SYSTEM_PROMPT = "You are NIA, a concise, helpful AI colleague in a secure enterprise workspace."


async def stream_reply(messages: list[dict[str, str]]) -> AsyncIterator[str]:
    payload = {"model": OLLAMA_MODEL, "stream": True, "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages]}
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    item = json.loads(line)
                    text = item.get("message", {}).get("content", "")
                    if text:
                        yield text
    except httpx.HTTPError as error:
        raise RuntimeError("NIA is unavailable. Start Ollama and download the configured model.") from error
