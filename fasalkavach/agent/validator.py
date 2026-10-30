"""Guardrail: check the agent's advisory against the computed facts.

1. The recommended actions must be exactly the ones the decision engine approved.
2. Every number in the text must exist somewhere in the tool results
   (so the LLM cannot invent "80% chance" or "Rs 10,000 loss").
"""
import re

# Hindi (Devanagari) and Punjabi (Gurmukhi) digits -> ASCII
_DIGITS = str.maketrans("०१२३४५६७८९੦੧੨੩੪੫੬੭੮੯", "01234567890123456789")
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def extract_numbers(text: str) -> list[float]:
    text = text.translate(_DIGITS)
    return [float(m.replace(",", "")) for m in _NUMBER.findall(text)]


def _collect_allowed(obj, out: set):
    """Walk the facts and collect every number, plus the same number as a percentage."""
    if isinstance(obj, bool) or obj is None:
        return
    if isinstance(obj, (int, float)):
        out.add(float(obj))
        if 0 <= obj <= 1:
            out.add(round(obj * 100))
    elif isinstance(obj, str):
        for n in extract_numbers(obj):
            out.add(n)
        # Dates like 2026-03-14 -> also allow 14, 3, 2026
        for y, m, d in re.findall(r"(\d{4})-(\d{2})-(\d{2})", obj):
            out.update({float(y), float(m), float(d)})
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect_allowed(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _collect_allowed(v, out)


def _matches(n: float, allowed: set) -> bool:
    # Allow small counts ("2 days"). Percentages and other numbers under 100 must
    # match exactly; rupee amounts may be rounded (4,860 -> "about 4,900").
    if n <= 10:
        return True
    return any(abs(n - a) <= (0.5 if abs(a) < 100 else 0.03 * abs(a)) for a in allowed)


def validate_advisory(advisory: dict, facts: dict) -> list[str]:
    problems = []
    decision = facts.get("decision")
    if not decision:
        return ["evaluate_actions has not been run - call it before submitting"]

    approved = set(decision["recommended_actions"])
    known = {a["action_id"] for a in decision["actions"]}
    given = set(advisory.get("recommended_action_ids", []))
    for a in given - known:
        problems.append(f"'{a}' is not an action returned by evaluate_actions")
    for a in (given & known) - approved:
        problems.append(f"'{a}' is not worth its cost according to evaluate_actions - do not recommend it")
    for a in approved - given:
        problems.append(f"'{a}' was approved by evaluate_actions but is missing from your advisory")

    allowed: set = set()
    _collect_allowed(facts, allowed)
    text = " ".join(str(advisory.get(k, "")) for k in ("headline", "advisory_text", "answer_to_question"))
    bad = sorted({n for n in extract_numbers(text) if not _matches(n, allowed)})
    if bad:
        problems.append("These numbers do not appear in any tool result: "
                        + ", ".join(f"{b:g}" for b in bad) + ". Use only computed values.")
    return problems
