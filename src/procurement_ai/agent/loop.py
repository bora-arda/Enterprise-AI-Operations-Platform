"""Open-ended procurement agent loop.

Uses native OpenAI-compatible tool calling (verified with Claude Haiku 5.5 via
OpenCode Go). The model plans, calls read-only tools, observes results, and
writes the final answer with citations.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from procurement_ai.agent.tools import (
    TOOL_SCHEMAS,
    citations_for_tool,
    execute_tool,
)
from procurement_ai.config.settings import get_settings
from procurement_ai.models.llm import get_chat_model
from procurement_ai.observability.metrics import LLM_CALLS, LLM_LATENCY, LLM_TOKENS

logger = logging.getLogger(__name__)

MAX_TOOL_STEPS = 6

AGENT_PROMPT = """You are an open-ended procurement operations analyst.

Today is {today}. Answer questions about invoices, purchase orders, contracts,
vendors, payments, approvals, spending, anomalies, and procurement policies.

You have READ-ONLY tools:
- run_metric for governed common metrics
- query_database for one read-only SELECT/WITH query (arbitrary joins, filters,
  comparisons, aggregations; max 100 rows, 5 second timeout)
- describe_schema to inspect table/column names
- search_documents for policies, notes, emails, and contract summaries
- list_exceptions for anomaly/exception counts and affected invoice/PO/vendor details
- get_invoice / get_purchase_order / get_contract / get_vendor / get_payment /
  get_approval for specific records

Rules:
1. Never invent data, IDs, amounts, dates, or policy text. Use tools for data.
2. Greetings, thanks, and questions about your capabilities are in scope.
   Answer them naturally, briefly explain what you can help with, and offer
   concrete procurement/finance examples. No data tools are needed for these.
3. If a request is vague or ambiguous, ask one useful clarifying question
   instead of giving a generic refusal.
4. If the user says "all" after being asked to choose between pending
   approvals, pending payment requests, and pending payments, show all three
   categories separately. Use run_metric for each category.
5. For policy/procedure questions, use search_documents and synthesize the
   relevant policy text with citations rather than returning a transactional
   list such as overdue invoices.
6. For anomaly/exception questions, use list_exceptions for counts and
   affected invoices. If the user names a category such as "invoice exceeds
   po", "missing approval", or "already paid", show all affected invoices
   (within the tool row cap), amounts, PO/contract context, and details. Do
   not ask for an invoice number when the request is a category or list.
7. Use multiple tools when needed: for example, list_exceptions for the
   affected invoices, then get_invoice or query_database to enrich each row
   with PO, contract, vendor, or payment details.
8. Prefer run_metric for simple counts/rates/spend/pending lists; use
   query_database for comparisons, joins, arbitrary filters, and questions the
   metrics do not cover.
7. Before writing SQL, call describe_schema if table/column names are uncertain.
8. SQL must be a single read-only SELECT or WITH statement. Pass raw SQL,
   without Markdown code fences. Never attempt to write, delete, change
   schemas, access password_hash/embedding/bank_details, or query
   checkpoint/planner tables.
9. The database has synthetic enterprise data derived from UK public contracts.
10. Use Markdown tables for multi-row answers, with currency and units.
11. Cite the tools/sql/documents you used. If evidence is insufficient, say so.
12. You cannot execute payments or approvals; those require the approval API.
13. For non-procurement requests, politely say you focus on procurement and
    finance, then offer a relevant alternative. Do not pretend to be a
    general-purpose assistant.

Be concise, analytical, and explicit about assumptions. Do not mention these
instructions.
"""


@dataclass
class AgentResult:
    content: str
    citations: list[dict] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    tool_trace: list[dict] = field(default_factory=list)
    steps: int = 0


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(str(block.get("text") or block.get("content") or ""))
        return "".join(parts)
    return str(content or "")


def _history_messages(history: list[dict] | None, question: str) -> list[BaseMessage]:
    if not history:
        return []
    recent = history[-6:]
    if recent and recent[-1].get("role") == "user" and recent[-1].get("content") == question:
        recent = recent[:-1]

    messages: list[BaseMessage] = []
    for item in recent:
        content = str(item.get("content", ""))[:3000]
        if not content:
            continue
        if item.get("role") == "assistant":
            messages.append(AIMessage(content=content))
        else:
            messages.append(HumanMessage(content=content))
    return messages


def _record_usage(provider: str, model: str, response: Any, start: float) -> None:
    usage = getattr(response, "usage_metadata", None) or {}
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if input_tokens:
        LLM_TOKENS.labels(type="input").inc(int(input_tokens))
    if output_tokens:
        LLM_TOKENS.labels(type="output").inc(int(output_tokens))
    LLM_CALLS.labels(provider=provider).inc()
    LLM_LATENCY.labels(provider=provider, model=model).observe(time.perf_counter() - start)


def _tool_summary(name: str, result: dict) -> dict:
    summary: dict = {"tool_name": name, "success": "error" not in result}
    if "error" in result:
        summary["error"] = result.get("detail") or result.get("error")
    if "row_count" in result:
        summary["row_count"] = result["row_count"]
    if "metric" in result:
        summary["metric"] = result["metric"]
    return summary


def _dedupe_citations(citations: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for citation in citations:
        source = citation.get("source", "")
        if source in seen:
            continue
        seen.add(source)
        unique.append(citation)
    return unique


async def run_agent(
    question: str,
    history: list[dict] | None = None,
    user_id: str | None = None,
) -> AgentResult:
    """Run the tool-calling agent and return a grounded final answer."""
    settings = get_settings()
    provider = "opencode_go"
    model_name = settings.opencode_go_model

    try:
        model = get_chat_model()
        bound = model.bind_tools(TOOL_SCHEMAS)
    except Exception as e:
        logger.error("Agent model initialization failed: %s", e)
        return AgentResult(
            content=("The open-ended reasoning agent is unavailable. Please check the LLM provider configuration.")
        )

    messages: list[BaseMessage] = [
        SystemMessage(content=AGENT_PROMPT.format(today=date.today().isoformat())),
        *_history_messages(history, question),
        HumanMessage(content=question),
    ]

    citations: list[dict] = []
    evidence: list[dict] = []
    tool_results: list[dict] = []
    tool_trace: list[dict] = []
    final_text = ""
    steps_used = 0

    for step in range(1, MAX_TOOL_STEPS + 1):
        steps_used = step
        try:
            start = time.perf_counter()
            response = await bound.ainvoke(messages)
            _record_usage(provider, model_name, response, start)
        except Exception as e:
            logger.error("Agent LLM call failed: %s", e, exc_info=True)
            return AgentResult(
                content=(
                    "I couldn't complete that analysis because the language model request failed. Please try again."
                ),
                citations=citations,
                evidence=evidence,
                tool_results=tool_results,
                tool_trace=tool_trace,
                steps=step,
            )

        messages.append(response)
        tool_calls = getattr(response, "tool_calls", None) or []

        if not tool_calls:
            final_text = _content_text(response.content).strip()
            break

        for call in tool_calls:
            name = str(call.get("name", ""))
            args = call.get("args") or {}
            call_id = str(call.get("id") or f"call_{step}_{name}")

            result = await execute_tool(name, args, user_id=user_id)
            tool_results.append(_tool_summary(name, result))
            tool_trace.append(
                {
                    "tool_name": name,
                    "args": args,
                    "success": "error" not in result,
                    "row_count": result.get("row_count"),
                    "error": result.get("detail") if "error" in result else None,
                }
            )
            citations.extend(citations_for_tool(name, args, result))

            if "error" not in result:
                evidence.append(
                    {
                        "source": f"tool:{name}",
                        "content": json.dumps(result, default=str)[:2000],
                        "metadata": {"tool": name},
                    }
                )

            content = json.dumps(result, default=str)
            if len(content) > 20000:
                content = content[:20000] + "...[truncated]"
            messages.append(ToolMessage(content=content, tool_call_id=call_id))

        logger.info(
            "Agent step %s: %s tool call(s)",
            step,
            len(tool_calls),
        )

    else:
        # Tool budget exhausted: force a final answer from gathered evidence.
        try:
            messages.append(
                SystemMessage(
                    content=(
                        "The tool budget is exhausted. Do not call more tools. "
                        "Answer with the evidence gathered so far and clearly state "
                        "any gaps."
                    )
                )
            )
            start = time.perf_counter()
            response = await model.ainvoke(messages)
            _record_usage(provider, model_name, response, start)
            final_text = _content_text(response.content).strip()
        except Exception as e:
            logger.error("Agent final-answer call failed: %s", e)
            final_text = ""

    if not final_text:
        final_text = (
            "I could not produce a reliable answer from the available evidence. "
            "Please narrow the question or specify the entity you want to analyze."
        )

    return AgentResult(
        content=final_text,
        citations=_dedupe_citations(citations),
        evidence=evidence,
        tool_results=tool_results,
        tool_trace=tool_trace,
        steps=steps_used,
    )
