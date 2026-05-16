from .config import settings
from .exceptions import CostCapExceeded


def check_cost(tier: str, current_cost: float) -> None:
    """Raise CostCapExceeded before any LLM call that would exceed the tier cap."""
    cap = settings.cost_cap(tier)
    if current_cost >= cap:
        raise CostCapExceeded(tier=tier, cap=cap, current=current_cost)


def remaining_budget(tier: str, current_cost: float) -> float:
    return max(0.0, settings.cost_cap(tier) - current_cost)
