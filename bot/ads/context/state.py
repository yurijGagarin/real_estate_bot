import json

from telegram.ext import ContextTypes


class State:
    def __init__(
        self,
        question_index=0,
        questions=None,
    ):
        self.question_index = question_index
        self.questions = questions if questions is not None else []

    def to_json(self):
        return json.dumps(
            {
                "i": self.question_index,
                "q": self.questions,
            }
        )

    @classmethod
    def from_json(cls, raw_data):
        data = json.loads(raw_data)

        return cls(
            question_index=data.get("i") or 0,
            questions=data.get("q") or [],
        )

    @classmethod
    def from_context(cls, context: ContextTypes.DEFAULT_TYPE):
        state = cls.from_json(context.user_data.get("question_state") or "{}")
        state.context = context
        return state

    def update_context(self, context: ContextTypes.DEFAULT_TYPE):
        context.user_data["question_state"] = self.to_json()
