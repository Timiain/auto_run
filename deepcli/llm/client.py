from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List

try:
    import openai
except Exception:
    openai = None

try:
    import tiktoken
except Exception:
    tiktoken = None

try:
    from ollama import Client as OllClient
except Exception:
    OllClient = None

openai_client = None
ollama_client = None


def calculate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    _ = (model, tokens_in, tokens_out)
    return 0.0


def save_token_result(tag: str, model: str, tokens_in: int, tokens_out: int, messages: List[dict], answer: str) -> str:
    logs = Path("token_logs")
    logs.mkdir(exist_ok=True)
    path = logs / f"{tag}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps({"model": model, "tokens_in": tokens_in, "tokens_out": tokens_out, "messages": messages, "answer": answer}, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def get_chat_response(api_key, base_url, model, messages, stream=False, temperature=0.7, num_ctx=24000, num_predict=4096):
    global openai_client, ollama_client

    system_prompt = messages[0]["content"] if messages and messages[0]["role"] == "system" else ""
    prompt = "".join([m["content"] for m in messages if m["role"] == "user"])

    if "ollama" in model:
        parts = re.split('#', model)
        if OllClient is None:
            return None
        if ollama_client is None:
            ollama_client = OllClient(host=base_url, headers={'x-some-header': 'some-value'})
        response = ollama_client.chat(model=parts[1], messages=messages, options={"temperature": temperature, "num_ctx": num_ctx, "num_predict": num_predict})
        if response:
            answer = response.message.content
        else:
            return None
    else:
        if openai is None:
            return None
        if openai_client is None:
            openai_client = openai.OpenAI(api_key=api_key, base_url=base_url)
        try:
            response = openai_client.chat.completions.create(model=model, messages=messages, stream=stream, temperature=temperature)
        except Exception:
            return None
        if response:
            answer = response.choices[0].message.content
        else:
            return None

    if tiktoken is None:
        save_token_result("default", model, 0, 0, messages, answer)
        return answer

    try:
        if model in ["o1-preview", "o1-mini", "claude-3.5-sonnet", "o1"]:
            encoding = tiktoken.encoding_for_model("gpt-4o")
        elif model == "deepseek-chat":
            encoding = tiktoken.get_encoding("cl100k_base")
        else:
            encoding = tiktoken.encoding_for_model(model)
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")

    tokens_in = len(encoding.encode(system_prompt + prompt))
    tokens_out = len(encoding.encode(answer))
    _ = calculate_cost(model, tokens_in, tokens_out)
    save_token_result("default", model, tokens_in, tokens_out, messages, answer)
    return answer
