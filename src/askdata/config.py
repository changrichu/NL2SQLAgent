"""Global configuration — load from .env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ---- LLM ----
    llm_provider: str = "deepseek"
    llm_model: str = ""

    openai_api_key: str = ""
    deepseek_api_key: str = ""
    dashscope_api_key: str = ""
    doubao_api_key: str = ""
    zhipu_api_key: str = ""

    # ---- PostgreSQL ----
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = ""
    postgres_user: str = ""
    postgres_password: str = ""

    # ---- Safety ----
    sql_max_rows: int = 10000
    sandbox_timeout: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def get(self, key: str, default: str = "") -> str:
        env_map = {
            "OPENAI_API_KEY": self.openai_api_key,
            "DEEPSEEK_API_KEY": self.deepseek_api_key,
            "DASHSCOPE_API_KEY": self.dashscope_api_key,
            "DOUBAO_API_KEY": self.doubao_api_key,
            "ZHIPU_API_KEY": self.zhipu_api_key,
        }
        return env_map.get(key, default)


settings = Settings()
