from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    grok_api_key: str = ""
    grok_api_base: str = "https://api.groq.com/openai/v1"
    grok_model: str = "grok-2-latest"

    env: str = "development"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    university_name: str = "Guru Nanak Dev University"
    app_name: str = "AcadEase AI"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

print("GROK_API_KEY:", settings.grok_api_key)
print("GROK_API_BASE:", settings.grok_api_base)
print("GROK_MODEL:", settings.grok_model)