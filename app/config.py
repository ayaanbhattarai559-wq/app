from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "stockflow"
    db_password: str = "change-me"
    db_name: str = "stockflow"

    # Path to a CA certificate file, needed for hosts like Aiven that require
    # SSL for external connections. Leave blank for plain local MySQL.
    db_ssl_ca: str = ""

    cors_origins: str = "http://localhost:5173"

    auto_create_tables: bool = True
    seed_on_startup: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
