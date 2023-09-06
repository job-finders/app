from pydantic import Field
from pydantic import BaseSettings


class MySQLSettings(BaseSettings):
    PRODUCTION_DB: str = Field(..., env="production_sql_db")
    DEVELOPMENT_DB: str = Field(..., env="dev_sql_db")

    class Config:
        env_file = '.env.developer'
        env_file_encoding = 'utf-8'


class ResendSettings(BaseSettings):
    API_KEY: str = Field(..., env="RESEND_API_KEY")
    from_: str = Field(default="norespond@rental-manager.site")

    class Config:
        env_file = '.env.developer'
        env_file_encoding = 'utf-8'


class EmailSettings(BaseSettings):
    RESEND: ResendSettings = ResendSettings()

    class Config:
        env_file = '.env.developer'
        env_file_encoding = 'utf-8'


class Settings(BaseSettings):
    APP_NAME: str = Field(default='Job Finders')
    LOGO_URL: str = Field(default="https://rental-manager.site/static/images/custom/logo.png")
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    CLIENT_SECRET: str = Field(..., env="CLIENT_SECRET")
    DEVELOPMENT_SERVER_NAME: str = Field(default="DESKTOP-T9V7F59")
    HOST_ADDRESSES: str = Field(..., env='HOST_ADDRESSES')
    MYSQL_SETTINGS: MySQLSettings = MySQLSettings()
    EMAIL_SETTINGS: EmailSettings = EmailSettings()

    class Config:
        env_file = '.env.developer'
        env_file_encoding = 'utf-8'


def config_instance() -> Settings:
    """
    :return:
    """
    return Settings()
