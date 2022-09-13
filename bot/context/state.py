import json

from telegram.ext import ContextTypes


class State:
    def __init__(
        self,
        result_sliced_view=None,
        filter_index=0,
        filters=None,
        is_subscription=False,
    ):
        self.result_sliced_view = result_sliced_view
        self.filter_index = filter_index
        self.filters = filters if filters is not None else []
        self.is_subscription = is_subscription

    def to_json(self):
        return json.dumps(
            {
                "rsv": self.result_sliced_view,
                "i": self.filter_index,
                "f": self.filters,
                "sbcsr_mode": self.is_subscription,
            }
        )

    @classmethod
    def from_json(cls, raw_data):
        data = json.loads(raw_data)

        return cls(
            result_sliced_view=data.get("rsv"),
            filter_index=data.get("i") or 0,
            filters=data.get("f") or [],
            is_subscription=data.get("sbcsr_mode"),
        )

    @classmethod
    def from_context(cls, context: ContextTypes.DEFAULT_TYPE):
        state = cls.from_json(context.user_data.get("filter_state") or "{}")
        state.context = context
        return state

    def update_context(self, context: ContextTypes.DEFAULT_TYPE):
        context.user_data["filter_state"] = self.to_json()
