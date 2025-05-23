from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class MySQLSettings(BaseSettings):
    PRODUCTION_DB: str = Field(..., alias="PRODUCTION_SQL_DB")
    DEVELOPMENT_DB: str = Field(..., alias="DEV_SQL_DB")

    model_config = SettingsConfigDict(
        env_file=".env.developer",
        env_file_encoding="utf-8",
        extra="ignore"
    )


class ResendSettings(BaseSettings):
    API_KEY: str = Field(..., alias="RESEND_API_KEY")
    from_: str = Field("norespond@jobfinders.site", alias="RESEND_FROM_EMAIL")

    model_config = SettingsConfigDict(
        env_file=".env.developer",
        env_file_encoding="utf-8",
        extra="ignore"
    )


class EmailSettings(BaseSettings):
    ADMIN_EMAIL: str = Field(default="admin@jobfinders.site")
    RESEND: ResendSettings = Field(default_factory=ResendSettings)

    model_config = SettingsConfigDict(
        env_file=".env.developer",
        env_file_encoding="utf-8",
        extra="ignore"
    )


class RedisSettings(BaseSettings):
    REDIS_URL: str = Field(..., alias="REDIS_URL")

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
    IS_DEVELOPMENT_SERVER: bool = Field(..., alias="IS_DEVELOPMENT_SERVER")
    HOST_ADDRESSES: str
    MYSQL_SETTINGS: MySQLSettings = Field(default_factory=MySQLSettings)
    EMAIL_SETTINGS: EmailSettings = Field(default_factory=EmailSettings)
    REDIS: RedisSettings = Field(default_factory=RedisSettings)
    ACTIVITY_RETENTION_DAYS: int = 180
    ACTIVITY_CACHE_TTL: int = 3600  # 1 hour

    model_config = SettingsConfigDict(
        env_file=".env.developer",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def config_instance() -> Settings:
    return Settings()
