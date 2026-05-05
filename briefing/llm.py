"""LLM client — supports Anthropic Claude, OpenAI, and Azure OpenAI."""
from __future__ import annotations

import os


def call_llm(messages: list[dict[str, str]]) -> str:
    """
    Call the configured LLM provider and return the response text.

    Provider selection (first match wins):
      1. ANTHROPIC_API_KEY set → Anthropic Claude
      2. AZURE_OPENAI_ENDPOINT set → Azure OpenAI
      3. Default → OpenAI
    """
    if os.environ.get("ANTHROPIC_API_KEY", "").strip():
        return _call_anthropic(messages)
    if os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip():
        return _call_azure(messages)
    return _call_openai(messages)


def _call_anthropic(messages: list[dict[str, str]]) -> str:
    import anthropic

    system = ""
    user_messages = []
    for m in messages:
        if m["role"] == "system":
            system = m["content"]
        else:
            user_messages.append(m)

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")

    response = client.messages.create(
        model=model,
        max_tokens=1500,
        system=system,
        messages=user_messages,
    )
    return response.content[0].text


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
