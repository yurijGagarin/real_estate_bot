import json

from telegram.ext import ContextTypes


class State:

    def __init__(self, result_sliced_view=0, page_idx=0, filter_index=0, filters=None):
        self.result_sliced_view = result_sliced_view
        self.page_idx = page_idx
        self.filter_index = filter_index
        self.filters = filters if filters is not None else []

    def to_json(self):
        return json.dumps({
            'rsv': self.result_sliced_view,
            'i': self.filter_index,
            'f': self.filters,
            'p': self.page_idx
        })

    @classmethod
    def from_json(cls, raw_data):
        data = json.loads(raw_data)

        return cls(
            result_sliced_view=data.get('rsv') or 0,
            page_idx=data.get('p') or 0,
            filter_index=data.get('i') or 0,
            filters=data.get('f') or []
        )

    @classmethod
    def from_context(cls, context: ContextTypes.DEFAULT_TYPE):
        state = cls.from_json(context.user_data.get('filter_state') or '{}')
        state.context = context
        return state

    def update_context(self, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['filter_state'] = self.to_json()
