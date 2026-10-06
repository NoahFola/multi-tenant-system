from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    JWT_SECRET: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    
    FIRESTORE_EMULATOR_HOST: str = ""
    GOOGLE_CLOUD_PROJECT: str
    
    REDIS_URL: str
    
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str
    
    APP_BASE_URL: str

    class Config:
        env_file = ".env"

settings = Settings()
