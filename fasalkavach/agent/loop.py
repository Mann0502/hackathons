"""The agent loop: Claude plans which tools to call, we run them, and repeat
until it submits an advisory that passes validation.

Written as a plain loop (no framework) so every step is easy to follow:
  1. send conversation + tool list to Claude
  2. Claude replies with tool calls  -> run them, send results back
  3. Claude calls submit_advisory    -> validate; if it fails, send the problems back
  4. stop when the advisory passes, or fall back to the rule-based path
"""
import json
import time

import anthropic

from config import AGENT_MAX_STEPS, AGENT_MAX_VALIDATION_RETRIES, LLM_MODEL

from .tools import TOOL_SCHEMAS, FarmSession, ToolError
from .validator import validate_advisory

LANGUAGE_NAMES = {"en": "English", "hi": "Hindi (Devanagari script)", "pa": "Punjabi (Gurmukhi script)"}

SYSTEM_PROMPT = """You are FasalKavach, a crop-protection advisor for farmers in Punjab, India.

Your job: gather live data with the tools, run the decision engine, then explain the result to the farmer.

How to work:
- Call independent tools in parallel when you can (e.g. soil moisture and mandi price).
- If a tool returns an error, read it and recover: call the missing prerequisite, or continue without optional data (soil moisture) and mention it.
- Never calculate probabilities or rupee amounts yourself. Only quote numbers that appear in tool results.
- Recommend exactly the actions that evaluate_actions marked recommended=true. If none are, say no action is needed and the farmer can work normally.
- Write for a farmer: short, plain sentences, concrete days and actions, no jargon. Round rupees sensibly.
- Finish by calling submit_advisory. If it reports problems, fix them and call it again."""


class AgentUnavailable(RuntimeError):
    pass


def _user_message(req: dict) -> str:
    lines = [
        "Farmer's request:",
        f"- Location: {req.get('place_name') or ''} lat={req.get('lat')} lon={req.get('lon')}",
        f"- Crop: {req['crop']}, planted on {req['planted_on']}",
        f"- Area: {req['area_acres']} acres",
        f"- Usual yield: {req.get('yield_q_per_acre') or 'unknown'} quintal/acre",
        f"- Reply language: {LANGUAGE_NAMES.get(req.get('language', 'en'), 'English')} (language code '{req.get('language', 'en')}')",
    ]
    if req.get("question"):
        lines.append(f"- Farmer's question: {req['question']}")
    return "\n".join(lines)


def _summarise(result) -> str:
    s = json.dumps(result, default=str)
    return s if len(s) <= 300 else s[:300] + "..."


def run_agent(req: dict, session: FarmSession) -> dict:
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": _user_message(req)}]
    trace = []
    validation_failures = 0
    nudged = False

    for step in range(AGENT_MAX_STEPS):
        try:
            response = client.beta.messages.create(
                model=LLM_MODEL,
                max_tokens=16000,
                system=SYSTEM_PROMPT,
                tools=TOOL_SCHEMAS,
                messages=messages,
                output_config={"effort": "low"},
                # If the model declines, the API retries on a fallback model automatically
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.APIError as e:
            raise AgentUnavailable(f"LLM API error: {e}")

        if response.stop_reason == "refusal":
            raise AgentUnavailable("LLM declined the request")
        if response.stop_reason == "max_tokens":
            raise AgentUnavailable("LLM response was cut off")

        # Keep the full assistant turn (including thinking blocks) in the history
        messages.append({"role": "assistant", "content": response.content})
        tool_calls = [b for b in response.content if b.type == "tool_use"]

        if not tool_calls:
            if nudged:
                raise AgentUnavailable("Agent stopped without submitting an advisory")
            nudged = True
            messages.append({"role": "user", "content": "Please finish by calling submit_advisory."})
            continue

        results = []
        final = None
        for call in tool_calls:
            started = time.time()
            is_error = False
            if call.name == "submit_advisory":
                problems = validate_advisory(call.input, session.facts())
                if problems:
                    validation_failures += 1
                    is_error = True
                    output = {"accepted": False, "problems": problems}
                    if validation_failures > AGENT_MAX_VALIDATION_RETRIES:
                        raise AgentUnavailable("Advisory failed validation repeatedly: " + "; ".join(problems))
                else:
                    output = {"accepted": True}
                    final = call.input
            else:
                try:
                    method = getattr(session, call.name, None)
                    if method is None:
                        raise ToolError(f"Unknown tool {call.name}")
                    output = method(**call.input)
                except ToolError as e:
                    is_error = True
                    output = {"error": str(e)}
                except TypeError as e:  # wrong arguments from the model
                    is_error = True
                    output = {"error": f"Bad arguments: {e}"}

            trace.append({"step": step + 1, "tool": call.name, "input": call.input,
                          "ok": not is_error, "result": _summarise(output),
                          "ms": round((time.time() - started) * 1000)})
            results.append({"type": "tool_result", "tool_use_id": call.id,
                            "content": json.dumps(output, default=str), "is_error": is_error})

        if final:
            return {"advisory": final, "trace": trace, "mode": "agent", "llm_steps": step + 1}
        # All results for this turn go back in ONE user message
        messages.append({"role": "user", "content": results})

    raise AgentUnavailable(f"Agent did not finish within {AGENT_MAX_STEPS} steps")
