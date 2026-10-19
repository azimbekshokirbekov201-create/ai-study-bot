from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

Code = Annotated[str, Field(min_length=1, max_length=80, pattern=r"^[a-z0-9_-]+$")]
Level = Annotated[str, Field(pattern=r"^(A1|A2|B1|B2|C1)$")]


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OptionInput(Payload):
    text_uz: str = Field(min_length=1, max_length=300)
    text_en: str = Field(min_length=1, max_length=300)


class QuestionInput(Payload):
    code: Code
    subject_id: int = Field(gt=0)
    lesson_id: int | None = None
    topic: Code
    level: Level | None = None
    difficulty: int = Field(ge=1, le=3)
    prompt_uz: str = Field(min_length=1, max_length=2500)
    prompt_en: str = Field(min_length=1, max_length=2500)
    options: list[OptionInput] = Field(min_length=4, max_length=4)
    correct_option: int = Field(ge=0, le=3)
    explanation_uz: str = Field(min_length=1, max_length=2000)
    explanation_en: str = Field(min_length=1, max_length=2000)
    active: bool = True
    premium_only: bool = False

    @model_validator(mode="after")
    def check_options(self):
        for lang in ("uz", "en"):
            options = [getattr(o, f"text_{lang}").strip() for o in self.options]
            if len(set(options)) != 4:
                raise ValueError("Four distinct options are required")
            if len(getattr(self, f"prompt_{lang}")) + sum(map(len, options)) > 3500:
                raise ValueError("Question and options exceed Telegram message size")
        return self


class SubjectInput(Payload):
    code: Code
    title_uz: str = Field(min_length=1, max_length=160)
    title_en: str = Field(min_length=1, max_length=160)
    active: bool = True


class LessonInput(Payload):
    code: Code
    subject_id: int = Field(gt=0)
    topic: Code
    level: Level | None = None
    title_uz: str = Field(min_length=1, max_length=160)
    title_en: str = Field(min_length=1, max_length=160)
    body_uz: str = Field(min_length=1, max_length=10000)
    body_en: str = Field(min_length=1, max_length=10000)
    audio_script: str | None = Field(default=None, max_length=4000)
    active: bool = True
    premium_only: bool = False


class GrantInput(Payload):
    telegram_id: int = Field(gt=0)
    days: int = Field(ge=1, le=366)
    reason: str = Field(min_length=5, max_length=500)


class BroadcastInput(Payload):
    text: str = Field(min_length=1, max_length=3500)
