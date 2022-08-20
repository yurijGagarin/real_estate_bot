class MessageNotFound(Exception):
    message_link: str

    def __init__(self, message_link: str):
        super().__init__()
        self.message_link = message_link
