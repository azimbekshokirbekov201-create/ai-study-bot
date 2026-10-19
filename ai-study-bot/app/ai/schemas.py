from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Criterion(StrictModel):
    score: float = Field(ge=0, le=9, multiple_of=0.5)
    feedback: str


class Mistake(StrictModel):
    original: str
    correction: str
    reason: str


class IELTSFeedback(StrictModel):
    task_achievement_response: Criterion
    coherence_cohesion: Criterion
    lexical_resource: Criterion
    grammatical_range_accuracy: Criterion
    mistakes: list[Mistake]
    improved_examples: list[str]
    recommendations: list[str]

    @property
    def estimated_band(self):
        # This is a practice estimate. Round the average to the nearest half-band.
        scores = [
            self.task_achievement_response.score,
            self.coherence_cohesion.score,
            self.lexical_resource.score,
            self.grammatical_range_accuracy.score,
        ]
        import math

        return math.floor(sum(scores) / 4 * 2 + 0.5) / 2

    def render(self, language="uz"):
        label = (
            "AI taxminiy bahosi — rasmiy IELTS natijasi emas."
            if language == "uz"
            else "AI estimate — not an official IELTS result."
        )
        text = f"{label}\nEstimated band: {self.estimated_band:.1f}\n"
        for name, item in [
            ("Task Achievement / Task Response", self.task_achievement_response),
            ("Coherence and Cohesion", self.coherence_cohesion),
            ("Lexical Resource", self.lexical_resource),
            ("Grammatical Range and Accuracy", self.grammatical_range_accuracy),
        ]:
            text += f"\n{name}: {item.score:.1f}\n{item.feedback}\n"
        text += "\n" + ("Xatolar:" if language == "uz" else "Specific mistakes:")
        for mistake in self.mistakes:
            text += f"\n• {mistake.original} → {mistake.correction}\n{mistake.reason}"
        text += "\n\n" + ("Yaxshilangan misollar:" if language == "uz" else "Improved examples:")
        text += "\n" + "\n".join(f"• {s}" for s in self.improved_examples)
        text += "\n\n" + ("Tavsiyalar:" if language == "uz" else "Recommendations:")
        return text + "\n" + "\n".join(f"• {s}" for s in self.recommendations)
