import asyncio
from dataclasses import dataclass

from openai import AsyncOpenAI

from app.ai.schemas import IELTSFeedback
from app.config import Settings


@dataclass
class Completion:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


class OpenAIProvider:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = (
            AsyncOpenAI(
                api_key=settings.openai_api_key.get_secret_value(),
                timeout=settings.ai_timeout_seconds,
                max_retries=0,
            )
            if settings.openai_api_key
            else None
        )

    @property
    def available(self):
        return self.client is not None

    async def complete(self, messages: list[dict], *, writing=False):
        kwargs = {}
        if writing:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "ielts_feedback",
                    "strict": True,
                    "schema": IELTSFeedback.model_json_schema(),
                },
            }
        async with asyncio.timeout(self.settings.ai_timeout_seconds):
            response = await self.client.chat.completions.create(
                model=self.settings.openai_model,
                messages=messages,
                max_completion_tokens=self.settings.ai_max_output_tokens,
                **kwargs,
            )
        choice = response.choices[0]
        if choice.finish_reason == "length":
            raise ValueError("Output exceeded configured limit")
        if choice.message.refusal or not choice.message.content:
            raise ValueError("No educational response")
        return Completion(
            choice.message.content,
            response.usage.prompt_tokens if response.usage else 0,
            response.usage.completion_tokens if response.usage else 0,
        )

    async def transcribe(self, data: bytes):
        async with asyncio.timeout(self.settings.ai_timeout_seconds):
            response = await self.client.audio.transcriptions.create(
                model=self.settings.transcription_model, file=("answer.ogg", data, "audio/ogg")
            )
        return response.text

    async def speech(self, text: str):
        async with asyncio.timeout(self.settings.ai_timeout_seconds):
            response = await self.client.audio.speech.create(
                model=self.settings.tts_model, voice="alloy", input=text, response_format="mp3"
            )
        return response.content

    async def close(self):
        if self.client:
            await self.client.close()
