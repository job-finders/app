from pydantic import Field
from pydantic import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = Field(default='Job Finders')
    LOGO_URL: str = Field(default="https://rental-manager.site/static/images/custom/logo.png")
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    CLIENT_SECRET: str = Field(..., env="CLIENT_SECRET")
    DEVELOPMENT_SERVER_NAME: str = Field(default="DESKTOP-T9V7F59")
    HOST_ADDRESSES: str = Field(..., env='HOST_ADDRESSES')

    class Config:
        env_file = '.env.development'
        env_file_encoding = 'utf-8'


def config_instance() -> Settings:
    """
    :return:
    """
    return Settings()
