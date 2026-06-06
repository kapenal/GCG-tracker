from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://gcg:gcg@localhost:5432/gcg_prices"
    cors_origins: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "https://gcg-tracker.vercel.app,"
        "https://gcg-tracker-eqkc7li0z-kapenals-projects.vercel.app"
    )
    fetch_delay_seconds: float = 2.0
    sync_timezone: str = "Asia/Seoul"
    sync_hour: int = 11
    sync_minute: int = 0
    sync_stale_hours: int = 24
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
