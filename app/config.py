from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, configurable via BREWFLOW_ environment variables."""

    data_dir: Path = Path("./data")
    database_url: str = ""

    @property
    def db_path(self) -> Path:
        return self.data_dir / "brewflow.db"

    @property
    def campaigns_dir(self) -> Path:
        d = self.data_dir / "campaigns"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def effective_database_url(self) -> str:
        return self.database_url or f"sqlite:///{self.db_path}"

    model_config = {"env_prefix": "BREWFLOW_"}


settings = Settings()
