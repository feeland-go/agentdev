from __future__ import annotations

from typing import Any

from .llm_client import call_llm
from .utils import parse_json_response


def generate_report(research_questions: list[str], synthesis_payload: str) -> dict[str, Any]:
    joined_questions = "\n".join(research_questions)
    prompt = f"QUESTIONS:\n{joined_questions}\n\nSYNTHESIS:\n{synthesis_payload}"
    result = parse_json_response(call_llm(prompt))
    if not result:
        result = {
            "answers": [],
            "overall_conclusion": "",
            "suggested_further_research": [],
        }
    return result
