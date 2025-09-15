from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field
from agents import Agent, ModelSettings


class ComposeEnvelope(BaseModel):
    to: List[str]
    subject: str
    body_text: str
    attach_paths: List[str] = Field(default_factory=list)
    include_raw_eml: bool = False


class ComposeDecision(BaseModel):
    is_relevant: bool
    reason: str
    task_markdown: str
    compose: Optional[ComposeEnvelope] = None


def build_triage_compose_agent(instructions: str, model: str) -> Agent:
    return Agent(
        name="Triage & Composer",
        instructions=instructions,
        output_type=ComposeDecision,
        model=model,
    )
