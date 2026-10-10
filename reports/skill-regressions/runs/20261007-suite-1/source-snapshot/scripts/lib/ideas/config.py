"""Public configuration for idea-pipeline topology and rendering limits."""
from __future__ import annotations

import re
from pathlib import Path

import yaml
from pydantic import Field, field_validator

from .models import SAFE_ID_PATTERN, StrictModel


class IdeaPipelineConfig(StrictModel):
    schema_version: str = Field(min_length=1)
    max_top_rows: int = Field(ge=1)
    lens_checklists: dict[str, list[str]] = Field(min_length=1)

    @field_validator("lens_checklists")
    @classmethod
    def validate_lens_ids(cls, value: dict[str, list[str]]) -> dict[str, list[str]]:
        for lens_id, questions in value.items():
            if not re.fullmatch(SAFE_ID_PATTERN, lens_id):
                raise ValueError(f"unsafe lens ID: {lens_id}")
            if not questions or len(questions) != len(set(questions)):
                raise ValueError(f"lens {lens_id} requires unique checklist IDs")
            for question_id in questions:
                if not re.fullmatch(SAFE_ID_PATTERN, question_id):
                    raise ValueError(f"unsafe checklist ID: {question_id}")
        return value


DEFAULT_PATH = Path(__file__).resolve().parents[3] / "config" / "idea_pipeline.yaml"


def load_idea_config(path: Path | None = None) -> IdeaPipelineConfig:
    config_path = path or DEFAULT_PATH
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise ValueError(f"cannot read idea pipeline config: {config_path}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid idea pipeline config: {config_path}") from exc
    return IdeaPipelineConfig.model_validate(raw)
