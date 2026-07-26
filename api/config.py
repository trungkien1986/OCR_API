from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str = "redis://redis:6379/0"
    storage_dir: str = "/data/storage"
    max_upload_mb: int = 25

    # Khoá Fernet mã hoá tenant_secret lúc lưu trữ (design/api.md Mục 9.4.3).
    # KHÔNG có giá trị mặc định — mất/thiếu khoá này thì không ký được webhook nào,
    # và không đoán bừa ra 1 khoá ngẫu nhiên mỗi lần khởi động (sẽ làm tenant_secret
    # đã mã hoá từ trước không giải mã lại được nữa).
    secret_encryption_key: str


settings = Settings()  # type: ignore[call-arg]  # đọc từ .env / biến môi trường lúc runtime
