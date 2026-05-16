from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database (SQLite)
    database_url: str = "sqlite+aiosqlite:///./goose.db"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Qdrant cloud
    qdrant_api_key: str = ""
    qdrant_cluster_id: str = ""  # full https:// URL
    qdrant_collection: str = "papers"
    qdrant_dedup_threshold: float = 0.92

    # Exa
    exa_api_key: str = ""
    exa_cache_ttl: int = 60 * 60 * 24 * 7  # 7 days

    # OpenRouter
    openrouter_api_key: str = ""

    # Auth — shared secret with NextAuth
    nextauth_secret: str = ""

    # Per-tier cost caps (USD)
    ultra_cost_cap: float = 1.50
    maverick_cost_cap: float = 0.30
    remi_cost_cap: float = 0.05

    def cost_cap(self, tier: str) -> float:
        return {"ultra": self.ultra_cost_cap, "maverick": self.maverick_cost_cap, "remi": self.remi_cost_cap}[tier]


settings = Settings()
