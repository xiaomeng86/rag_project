from __future__ import annotations

import json
from typing import Iterator

from openai import OpenAI

from config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, MODEL_PROVIDER


def _client() -> OpenAI:
    if not DASHSCOPE_API_KEY:
        raise RuntimeError("DASHSCOPE_API_KEY 未配置")
    return OpenAI(api_key=DASHSCOPE_API_KEY, base_url=DASHSCOPE_BASE_URL)


def stream_answer(prompt: str, question: str, citations: list[dict]) -> Iterator[tuple[str, str]]:
    if MODEL_PROVIDER == "mock":
        yield "thinking", "正在分析可核验的参考资料。"
        if citations:
            excerpt = citations[0]["content"].replace("\n", " ")[:180]
            yield "answer", f"根据文档资料：{excerpt} ##1$$"
        else:
            yield "answer", "没有找到可核验的参考资料，暂时无法基于文档回答。"
        return

    completion = _client().chat.completions.create(
        model="deepseek-r1",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    for chunk in completion:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        reasoning = getattr(delta, "reasoning_content", None)
        if reasoning:
            yield "thinking", reasoning
        if delta.content:
            yield "answer", delta.content


def recommended_questions(question: str) -> list[str]:
    if MODEL_PROVIDER == "mock":
        topic = question.strip()[:24] or "该主题"
        return [f"{topic}的关键依据是什么？", f"{topic}有哪些风险？", f"如何进一步验证{topic}？"]

    prompt = (
        "请围绕用户问题生成3个相关追问，只返回JSON对象，键为recommended_questions。\n"
        f"用户问题：{question}"
    )
    completion = _client().chat.completions.create(
        model="qwen2.5-7b-instruct",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        stream=False,
    )
    if not completion.choices:
        return []
    try:
        value = json.loads(completion.choices[0].message.content or "{}")
        questions = value.get("recommended_questions", [])
        return [str(item) for item in questions[:3]] if isinstance(questions, list) else []
    except json.JSONDecodeError:
        return []


def session_name(question: str) -> str:
    if MODEL_PROVIDER == "mock":
        return question.strip()[:24] or "新对话"
    prompt = f"请将下面问题概括成不超过20字的会话标题，只返回标题：{question}"
    completion = _client().chat.completions.create(
        model="qwen2.5-7b-instruct",
        messages=[{"role": "user", "content": prompt}],
        stream=False,
    )
    if not completion.choices:
        return question[:24]
    return (completion.choices[0].message.content or question).strip()[:24]

