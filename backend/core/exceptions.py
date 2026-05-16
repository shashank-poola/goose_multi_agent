class GooseError(Exception):
    pass


class CostCapExceeded(GooseError):
    def __init__(self, tier: str, cap: float, current: float):
        self.tier = tier
        self.cap = cap
        self.current = current
        super().__init__(f"Cost cap hit: ${current:.4f} >= ${cap} for tier '{tier}'")


class EmbeddingError(GooseError):
    pass


class QdrantError(GooseError):
    pass


class ExaError(GooseError):
    pass


class SessionNotFound(GooseError):
    pass


class AuthError(GooseError):
    pass
