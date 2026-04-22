from __future__ import annotations


def call_llm(prompt: str, model: str = "ccs glm") -> str:
    _ = model
    return (
        '{"summary":"placeholder","key_points":[],"key_entities":[],'
        '"contradictions":[],"gaps":[]}'
    ) if prompt else "{}"
