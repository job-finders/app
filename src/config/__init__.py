from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

# updated for version 2 pydantic
class MySQLSettings(BaseSettings):
    PRODUCTION_DB: str = Field(..., alias="production_sql_db")
    DEVELOPMENT_DB: str = Field(..., alias="dev_sql_db")

    model_config = SettingsConfigDict(
        env_file=".env.developer",
        env_file_encoding="utf-8",
        extra="ignore"
    )


class ResendSettings(BaseSettings):
    API_KEY: str = Field(..., alias="RESEND_API_KEY")
    from_: str = "norespond@jobfinders.site"

    model_config = SettingsConfigDict(
        env_file=".env.developer",
        env_file_encoding="utf-8",
        extra="ignore"
    )


class EmailSettings(BaseSettings):
    RESEND: ResendSettings = Field(default_factory=ResendSettings)

    model_config = SettingsConfigDict(
        env_file=".env.developer",
        env_file_encoding="utf-8",
        extra="ignore"
    )


class Settings(BaseSettings):
    APP_NAME: str = "Job Finders"
    LOGO_URL: str = "https://rental-manager.site/static/images/custom/logo.png"
    SECRET_KEY: str
    CLIENT_SECRET: str
    DEVELOPMENT_SERVER_NAME: str = "DESKTOP-T9V7F59"
    HOST_ADDRESSES: str
    MYSQL_SETTINGS: MySQLSettings = Field(default_factory=MySQLSettings)
    EMAIL_SETTINGS: EmailSettings = Field(default_factory=EmailSettings)

    model_config = SettingsConfigDict(
        env_file=".env.developer",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def config_instance() -> Settings:
    return Settings()
