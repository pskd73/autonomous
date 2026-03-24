import json
import os
import logging

from openai import OpenAI


logger = logging.getLogger(__name__)


class MemoryEngineInterface:
    def memorise(self, question: str, answer: str, facts: list[str]):
        pass

    def recall(self, question: str) -> str:
        pass


class DummyMemoryEngine(MemoryEngineInterface):
    def memorise(self, question: str, answer: str, facts: list[str]):
        logger.info(f"Memorising facts: {facts}")

    def recall(self, question: str) -> str:
        logger.info(f"Recalling facts for question: {question}")
        return ""


def extract_facts(question: str, answer: str) -> list[str]:
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        return []

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    system_prompt = (
        "Extract durable user-relevant facts from the conversation.\n"
        "Return facts that are useful for long-term memory.\n"
        "Rules:\n"
        "- Write every fact in first-person perspective, as if the user is speaking.\n"
        "- Use statements like 'I ...', 'My ...', 'I prefer ...', 'I work ...'.\n"
        "- Keep facts atomic and specific.\n"
        "- Exclude temporary, uncertain, or one-off details.\n"
        "- No duplicates.\n"
        "- Follow the JSON schema strictly."
    )

    user_prompt = (
        f"Question:\n{question}\n\n"
        f"Answer:\n{answer}\n\n"
        "Extract memory facts now."
    )

    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "memory_facts",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "facts": {
                            "type": "array",
                            "items": {"type": "string"},
                            "default": [],
                        }
                    },
                    "required": ["facts"],
                    "additionalProperties": False,
                },
            },
        },
    )

    content = (response.choices[0].message.content or "").strip()
    if not content:
        return []

    # Handle code-fenced JSON responses.
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:].strip()

    parsed = json.loads(content)

    if not isinstance(parsed, dict):
        return []
    parsed_facts = parsed.get("facts")
    if not isinstance(parsed_facts, list):
        return []

    facts: list[str] = []
    seen: set[str] = set()
    for item in parsed_facts:
        if not isinstance(item, str):
            continue
        fact = item.strip()
        if not fact:
            continue
        key = fact.lower()
        if key in seen:
            continue
        seen.add(key)
        facts.append(fact)

    return facts