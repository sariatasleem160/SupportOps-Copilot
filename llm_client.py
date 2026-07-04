"""Shared Anthropic client with JSON parsing, retry, and cost tracking."""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv(Path(__file__).resolve().parent / "config.env", override=True)

T = TypeVar("T", bound=BaseModel)

# Pricing per 1M tokens (USD) for claude-haiku-4-5 — update if model changes.
INPUT_COST_PER_M = 1.00
OUTPUT_COST_PER_M = 5.00
DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")


@dataclass
class LLMUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    model: str = DEFAULT_MODEL

    @property
    def estimated_cost_usd(self) -> float:
        return (
            self.input_tokens * INPUT_COST_PER_M / 1_000_000
            + self.output_tokens * OUTPUT_COST_PER_M / 1_000_000
        )


@dataclass
class SessionMetrics:
    records: list[dict[str, Any]] = field(default_factory=list)

    def add(self, ticket_id: str, usage: LLMUsage) -> None:
        self.records.append(
            {
                "ticket_id": ticket_id,
                "latency_ms": round(usage.latency_ms, 2),
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "estimated_cost_usd": round(usage.estimated_cost_usd, 6),
                "model": usage.model,
            }
        )

    def summary(self) -> dict[str, Any]:
        if not self.records:
            return {
                "count": 0,
                "median_latency_ms": 0,
                "total_cost_usd": 0,
                "avg_cost_per_ticket_usd": 0,
            }
        latencies = sorted(r["latency_ms"] for r in self.records)
        mid = len(latencies) // 2
        median = (
            latencies[mid]
            if len(latencies) % 2
            else (latencies[mid - 1] + latencies[mid]) / 2
        )
        total_cost = sum(r["estimated_cost_usd"] for r in self.records)
        return {
            "count": len(self.records),
            "median_latency_ms": round(median, 2),
            "total_cost_usd": round(total_cost, 6),
            "avg_cost_per_ticket_usd": round(total_cost / len(self.records), 6),
        }


SESSION_METRICS = SessionMetrics()


def _strip_markdown_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def parse_json_response(raw: str) -> dict[str, Any]:
    return json.loads(_strip_markdown_fences(raw))


def _build_messages(
    user_content: str,
    few_shot: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if few_shot:
        for example in few_shot:
            messages.append(
                {"role": "user", "content": example["customer_message"]}
            )
            messages.append(
                {"role": "assistant", "content": json.dumps(example["output"])}
            )
    messages.append({"role": "user", "content": user_content})
    return messages


def call_llm(
    system_prompt: str,
    user_content: str,
    *,
    few_shot: list[dict[str, Any]] | None = None,
    temperature: float = 0.2,
    model: str | None = None,
) -> tuple[str, LLMUsage]:
    """Call Anthropic Messages API and return raw text plus usage stats."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file."
        )

    import anthropic

    client = anthropic.Anthropic(api_key=api_key.strip())
    chosen_model = model or DEFAULT_MODEL
    messages = _build_messages(user_content, few_shot)

    start = time.perf_counter()
    response = client.messages.create(
        model=chosen_model,
        max_tokens=2048,
        system=f"{system_prompt}\n\nRespond with valid JSON only. No markdown fences.",
        messages=messages,
        temperature=temperature,
    )
    latency_ms = (time.perf_counter() - start) * 1000

    content = ""
    for block in response.content:
        if block.type == "text":
            content += block.text

    llm_usage = LLMUsage(
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        latency_ms=latency_ms,
        model=chosen_model,
    )
    return content or "{}", llm_usage


def call_llm_validated(
    system_prompt: str,
    user_content: str,
    schema: type[T],
    *,
    few_shot: list[dict[str, Any]] | None = None,
    temperature: float = 0.2,
    retry_prompt_template: str | None = None,
    ticket_id: str = "unknown",
) -> tuple[T, LLMUsage]:
    """Call LLM, validate with Pydantic, retry once on validation failure."""
    total_usage = LLMUsage()
    last_error: str | None = None
    retry_user_content = user_content

    for attempt in range(2):
        raw, usage = call_llm(
            system_prompt,
            retry_user_content,
            few_shot=few_shot if attempt == 0 else None,
            temperature=temperature,
        )
        total_usage.input_tokens += usage.input_tokens
        total_usage.output_tokens += usage.output_tokens
        total_usage.latency_ms += usage.latency_ms
        total_usage.model = usage.model

        try:
            data = parse_json_response(raw)
            result = schema.model_validate(data)
            SESSION_METRICS.add(ticket_id, total_usage)
            return result, total_usage
        except (ValidationError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            if attempt == 0 and retry_prompt_template:
                retry_user_content = (
                    f"{user_content}\n\n"
                    f"{retry_prompt_template.format(error=last_error)}"
                )
            else:
                break

    raise ValueError(f"LLM output failed validation after retry: {last_error}")
