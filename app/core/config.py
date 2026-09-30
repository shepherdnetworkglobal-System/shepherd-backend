from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Shepherd Network API"
    APP_ENV: str = "development"
    SECRET_KEY: str
    DATABASE_URL: str
    STELLAR_NETWORK: str = "testnet"
    STELLAR_HORIZON_URL: str = "https://horizon-testnet.stellar.org"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()