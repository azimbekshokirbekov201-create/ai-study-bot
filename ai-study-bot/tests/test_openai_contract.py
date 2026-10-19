import json

import httpx
from openai import AsyncOpenAI

from app.ai.provider import OpenAIProvider
from app.ai.schemas import IELTSFeedback


async def test_openai_sdk_request_and_structured_ielts_feedback(settings):
    criterion = {"score": 7.0, "feedback": "Clear position with relevant examples."}
    feedback = {
        key: criterion
        for key in (
            "task_achievement_response",
            "coherence_cohesion",
            "lexical_resource",
            "grammatical_range_accuracy",
        )
    }
    feedback |= {
        "mistakes": [
            {"original": "he go", "correction": "he goes", "reason": "Subject–verb agreement"}
        ],
        "improved_examples": ["He goes to school every day."],
        "recommendations": ["Review third-person verb forms."],
    }

    async def handler(request):
        body = json.loads(request.content)
        assert body["model"] == settings.openai_model
        assert body["max_completion_tokens"] == settings.ai_max_output_tokens
        assert body["response_format"]["json_schema"]["strict"] is True
        return httpx.Response(
            200,
            json={
                "id": "offline-test",
                "object": "chat.completion",
                "created": 1,
                "model": settings.openai_model,
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": json.dumps(feedback)},
                    }
                ],
                "usage": {"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
            },
        )

    provider = OpenAIProvider(settings)
    provider.client = AsyncOpenAI(
        api_key="test-only-key",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    result = await provider.complete([{"role": "user", "content": "Test essay"}], writing=True)
    evaluation = IELTSFeedback.model_validate_json(result.text)
    assert evaluation.estimated_band == 7.0
    assert "not an official IELTS result" in evaluation.render("en")
    assert "he go → he goes" in evaluation.render("en")
    await provider.close()
