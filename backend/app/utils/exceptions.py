class RateLimitException(Exception):
    def __init__(self, message: str, retry_after: str = None):
        self.message = message
        self.retry_after = retry_after
        super().__init__(self.message)
