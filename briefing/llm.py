"""LLM client — supports OpenAI and Azure OpenAI. Identical contract to tf-plan-ai-reviewer."""
from __future__ import annotations

import os


def call_llm(messages: list[dict[str, str]]) -> str:
    if os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip():
        return _call_azure(messages)
    return _call_openai(messages)


def _call_openai(messages: list[dict[str, str]]) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model = os.environ.get("MODEL", "gpt-4o")
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
        max_tokens=1500,
    )
    return response.choices[0].message.content or ""


def _call_azure(messages: list[dict[str, str]]) -> str:
    from openai import AzureOpenAI

    client = AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_KEY"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version="2024-02-01",
    )
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    response = client.chat.completions.create(
        model=deployment,
        messages=messages,
        temperature=0.2,
        max_tokens=1500,
    )
    return response.choices[0].message.content or ""
